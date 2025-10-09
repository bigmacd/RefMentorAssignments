from datetime import datetime as dtime
import mechanicalsoup
from typing import Tuple

from refWebSites import MySoccerLeague
from database import RefereeDbCockroach

initialized = False
allMatchData = None
games = None

db = RefereeDbCockroach()

def parseRefName(name: str) -> Tuple[str, str]:
    '''
    This handles all the idiosyncrasies of peoples names as configured
    in MSL.
    '''
    #st.write(f'refname: {name}')
    if name == '(requested)':
        return [None, None]
        
    # Remove extra spaces and trim
    name = ' '.join(name.split())
    
    # Handle comma-separated format like "Aguilera, Michael Jr."
    parts = name.split(',')
    if len(parts) > 1:
        # For "Last, First [Suffix]" format
        first_parts = parts[1].strip().split()
        return [first_parts[0], parts[0].strip()]
        
    # Handle format with no comma like "Michael Aguilera Jr."
    parts = name.split(' ')
    if len(parts) == 0:
        return [None, None]
    elif len(parts) == 1:
        return [parts[0], ""]
    elif len(parts) == 2:
        return [parts[0], parts[1]]
    else:
        # For names with more than two parts, check for common suffixes
        suffixes = ["Jr.", "Jr", "Sr.", "Sr", "III", "IV", "II"]
        if parts[-1] in suffixes:
            # If last part is a suffix, combine the middle parts as last name
            first_name = parts[0]
            last_name = ' '.join(parts[1:-1]) + ' ' + parts[-1]
            return [first_name, last_name]
        else:
            # Otherwise, first part is first name, rest is last name
            first_name = parts[0]
            last_name = ' '.join(parts[1:])
            return [first_name, last_name]


def getMatchData() -> dict:
    global initialized
    global allMatchData

    if not initialized:
        # get all the data we can
        br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
        br.addheaders = [('User-agent', 'Chrome')]
        site = MySoccerLeague(br)
        dates = site.getAllDatesForSeason()

        allMatchData = {}
        for date in dates:
            allMatchData[date] = site.getMatches(date)

        initialized = True
    return allMatchData


def getMentors() -> list:
    return db.getMentorsList()


def getCurrentDateIndex(dates: list) -> int:
    fs = "%A, %B %d, %Y"
    # get the current date in the same format as in MSL
    today = dtime.now()
    fd = today.strftime(fs)
    today = dtime.strptime(fd, fs)
    for index, d in enumerate(dates):
        thisDate = dtime.strptime(d, fs)
        if thisDate >= today:
            return index


def getVenues(allMatchData, dateKey):
    matches = allMatchData[dateKey]
    venues = list(matches.keys())
    venues = sorted(venues)
    return venues


def getGames(venueInfo, dateKey):

    global games
    matches = allMatchData[dateKey]
    games = matches[venueInfo]

    selectionList = []
    for game in games:
        selectionList.append(f"Time-{game['Time']}")
    return selectionList


def getReferees(game: str) -> tuple:

    gametime = game.split('-')[1]
    currentMatch = None

    for game in games:
        if game['Time'] == gametime:
             currentMatch = game
             break

    center = 'n/a'
    ar1 = 'n/a'
    ar2 = 'n/a'

    refname = currentMatch['Center']
    if refname != 'Not Used' and refname != 'None':
        center = parseRefName(refname)
    #    if db.findReferee(lname, fname):
    #        disabled = False

    refname = currentMatch['AR1']
    if refname != 'Not Used' and refname != 'None':
        ar1 = parseRefName(refname)
    #    if db.findReferee(lname, fname):
    #        disabled = False

    refname = currentMatch['AR2']
    if refname != 'Not Used' and refname != 'None':
        ar2 = parseRefName(refname)
    #    if db.findReferee(lname, fname):
    #        disabled = False

    return (center, ar1, ar2)
