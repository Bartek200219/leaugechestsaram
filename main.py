import requests
import urllib3
import json
from base64 import b64encode
from time import sleep
import os
import sys
from colorama import Fore, Back, Style
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
champions = []
championsOwnedWithoutChest = []
while not champions or len(champions) < 1:
    sleep(1)

    r = request('get', '/lol-champ-select/v1/all-grid-champions')

    if r.status_code != 200:
        continue

    champions = r.json()

for champion in champions:
    championsNames[champion['id']]=champion['name']
    if champion['disabled']:
        continue
    if not champion['owned']:
        continue
    if champion['masteryChestGranted']:
        continue
    championsOwnedWithoutChest.append(champion['id'])

###
# Main loop
#

championsInLobby = {}
while True:

    r = request('get', '/lol-gameflow/v1/gameflow-phase')

    if r.status_code != 200:
        if debug:
            print(Back.BLACK + Fore.RED + str(r.status_code) + Style.RESET_ALL, r.text)
        continue
    if debug:
        print(Back.BLACK + Fore.GREEN + str(r.status_code) + Style.RESET_ALL, r.text)

    phase = r.json()

    # Auto accept match
    if phase == 'ReadyCheck' and autoAccept:
        r = request('post', '/lol-matchmaking/v1/ready-check/accept')  # '/lol-lobby-team-builder/v1/ready-check/accept')
        print(Back.BLACK + Fore.GREEN + "Game accepted" + Style.RESET_ALL)
        championsInLobby = {}
    #check champions in 
    elif phase == 'ChampSelect':
        r = request('get', '/lol-champ-select/v1/session')
        if debug:
            print(r.status_code)
        if r.status_code != 200:
            if debug:
                print(Back.BLACK + Fore.RED + str(r.status_code) + Style.RESET_ALL, r.text)
            continue
        sesja = r.json()
        #check champions on bench
        for benchChampion in sesja['benchChampionIds']:
            if benchChampion in championsInLobby:
                continue
            if benchChampion in championsOwnedWithoutChest:
                championsInLobby[benchChampion]=True
            else:
                championsInLobby[benchChampion]=False
        #check other player champion
        for player in sesja['myTeam']:
            playerChampion = player['championId']
            if playerChampion in championsInLobby:
                continue
            if playerChampion in championsOwnedWithoutChest:
                championsInLobby[playerChampion]=True
            else:
                championsInLobby[playerChampion]=False
        #listChampions
        print(Fore.LIGHTMAGENTA_EX + "Champions in lobby" + Style.RESET_ALL)
        for champion in championsInLobby:
            if championsInLobby[champion]:
                print(Fore.GREEN + championsNames[champion] + Style.RESET_ALL)
            else:
                print(Fore.RED + championsNames[champion] + Style.RESET_ALL)
    else:
        print(Back.BLACK + Fore.YELLOW + "Waiting for champ select" + Style.RESET_ALL)
    sleep(0.3)    
    os.system("cls")
    