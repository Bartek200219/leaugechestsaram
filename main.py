from datetime import timedelta
import requests
import urllib3
import json
from base64 import b64encode
from time import sleep
import time
import datetime
import os
import sys
from colorama import Fore, Back, Style
from prettytable import PrettyTable
# Set to your game directory (where LeagueClient.exe is)
gamedirs = [r'M:\Gry\Riot Games\League of Legends',
            r'M:\Gry\Riot Games\League of Legends']
autoAccept = True
debug = False
###############################################################################
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Helper function
def request(method, path, query='', data=''):
    if not query:
        url = '%s://%s:%s%s' % (protocol, host, port, path)
    else:
        url = '%s://%s:%s%s?%s' % (protocol, host, port, path, query)

    if debug:
        print('%s %s %s' % (method.upper().ljust(7, ' '), url, data))
    # print(Back.BLACK + Fore.YELLOW + method.upper().ljust(7, ' ') + Style.RESET_ALL + ' ' + url + ' ' + data)

    fn = getattr(s, method)

    if not data:
        r = fn(url, verify=False, headers=headers)
    else:
        r = fn(url, verify=False, headers=headers, json=data)

    return r

def strdelta(tdelta):
    pass

###
# Read the lock file to retrieve LCU API credentials
#

lockfile = None
print('Waiting for League of Legends to start ..')

# Validate path / check that Launcher is started
while not lockfile:
    for gamedir in gamedirs:
        lockpath = r'%s\lockfile' % gamedir

        if not os.path.isfile(lockpath):
            continue

        print('Found running League of Legends, dir', gamedir)
        lockfile = open(r'%s\lockfile' % gamedir, 'r')

# Read the lock file data
lockdata = lockfile.read()
print(lockdata)
lockfile.close()

# Parse the lock data
lock = lockdata.split(':')

procname = lock[0]
pid = lock[1]

protocol = lock[4]
host = '127.0.0.1'
port = lock[2]

username = 'riot'
password = lock[3]

###
# Prepare Requests
#

# Prepare basic authorization header
userpass = b64encode(bytes('%s:%s' % (username, password), 'utf-8')).decode('ascii')
headers = { 'Authorization': 'Basic %s' % userpass }
print(headers['Authorization'])

# Create Request session
s = requests.session()

###
# Wait for login
#

# Check if logged in, if not then Wait for login
while True:
    sleep(1)
    r = request('get', '/lol-login/v1/session')

    if r.status_code != 200:
        print(r.status_code)
        continue

    # Login completed, now we can get data
    if r.json()['state'] == 'SUCCEEDED':
        break
    else:
        print(r.json()['state'])

###
# Get available champions
#
championsNames = {}
# 1: "Annie"
champions = {}
# 1: "id", "owned", "masteryLevel", "masteryPoints", "masteryChestGranted" ect.
result=[]
while not result or len(result) < 1:
    sleep(1)

    r = request('get', '/lol-champ-select/v1/all-grid-champions')

    if r.status_code != 200:
        continue

    result = r.json()

for champion in result:
    championsNames[champion['id']]=champion['name']
    champions[champion['id']]=champion

###
# Main loop
#
chestCount = 0 #how many chest can 
chestTime = 0 #time in epoch when next chest would be available
chestChecked = False
championsInLobby = []
while True:

    r = request('get', '/lol-gameflow/v1/gameflow-phase')

    if r.status_code != 200:
        if debug:
            print(Back.BLACK + Fore.RED + str(r.status_code) + Style.RESET_ALL, r.text)
        continue
    if debug:
        print(Back.BLACK + Fore.GREEN + str(r.status_code) + Style.RESET_ALL, r.text)

    phase = r.json()

    if not(chestChecked):
        #ernable chests
        result = request('get', '/lol-collections/v1/inventories/chest-eligibility')
        if result.status_code != 200:
            if debug:
                print(Back.BLACK + Fore.RED + str(result.status_code) + Style.RESET_ALL, result.text)
            continue
        result = result.json()
        chestCount = result["earnableChests"]
        chestTime = datetime.datetime.fromtimestamp(result["nextChestRechargeTime"]/1000)
        chestChecked = True

    # Auto accept match
    if phase == 'ReadyCheck' and autoAccept:
        r = request('post', '/lol-matchmaking/v1/ready-check/accept')  # '/lol-lobby-team-builder/v1/ready-check/accept')
        print(Back.BLACK + Fore.GREEN + "Game accepted" + Style.RESET_ALL)
        championsInLobby = []
    #check champions in 
    elif phase == 'ChampSelect':
        result = request('get', '/lol-champ-select/v1/session')
        if debug:
            print(r.status_code)
        if result.status_code != 200:
            if debug:
                print(Back.BLACK + Fore.RED + str(r.status_code) + Style.RESET_ALL, r.text)
            continue
        result = result.json()
        #champions on bench
        for benchChampion in result['benchChampionIds']:
            if benchChampion in championsInLobby:
                continue
            championsInLobby.append(benchChampion)
        #other player champions
        for player in result['myTeam']:
            playerChampion = player['championId']
            if playerChampion in championsInLobby:
                continue
            championsInLobby.append(playerChampion)
        #listChampions
        table = PrettyTable()
        table.field_names = [Fore.LIGHTMAGENTA_EX+ "Champions in lobby" + Style.RESET_ALL,Fore.CYAN + "Maestry Level"+ Style.RESET_ALL, Fore.LIGHTBLUE_EX + "Maestry Points" + Style.RESET_ALL]
        for champion in championsInLobby:
            if not(champions[champion]['masteryChestGranted']) and champions[champion]['owned']:
                table.add_row([Fore.GREEN + champions[champion]["name"] + Style.RESET_ALL, Fore.CYAN + str(champions[champion]["masteryLevel"]) + Style.RESET_ALL, Fore.LIGHTBLUE_EX + str(champions[champion]["masteryPoints"]) + Style.RESET_ALL])
            elif champions[champion]['masteryChestGranted']:
                table.add_row([Fore.YELLOW + champions[champion]["name"] + Style.RESET_ALL, Fore.CYAN + str(champions[champion]["masteryLevel"]) + Style.RESET_ALL, Fore.LIGHTBLUE_EX + str(champions[champion]["masteryPoints"]) + Style.RESET_ALL])
            else:
                table.add_row([Fore.RED + champions[champion]["name"] + Style.RESET_ALL,"None","None"])
        #timecalc
        now = datetime.datetime.now()
        timeToNextChest = chestTime - now
        #print
        if chestCount > 0:
            print(Fore.CYAN + "Eranable chests: " + chestCount + Style.RESET_ALL, end="\t") 
        else:
            print(Fore.YELLOW + "You don't have chests to earn -_-", end="\t")
        print(Fore.LIGHTBLUE_EX + "Time to next chest:" + str(timeToNextChest) + Style.RESET_ALL)
        print(table)
        print(Fore.GREEN + "Champion owned and chest NOT earned" + Style.RESET_ALL)
        print(Fore.YELLOW + "Champion owned and chest earned" + Style.RESET_ALL)
        print(Fore.RED + "Champion not owned" + Style.RESET_ALL)
    elif phase == "EndOfGame":
        chestChecked = False
        print(Back.BLACK + Fore.YELLOW + "Waiting for champ select" + Style.RESET_ALL)
    else:
        print(Back.BLACK + Fore.YELLOW + "Waiting for champ select" + Style.RESET_ALL)
    sleep(0.3)    
    if not(debug):
        os.system("cls")
    