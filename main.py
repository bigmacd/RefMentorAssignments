import datetime
import mechanicalsoup


from database import RefereeDbCockroach
from refWebSites import MySoccerLeague
from googleSheets import getRefsFromGoogleSignupSheet


import os
print(os.getcwd())

db = RefereeDbCockroach()

def getRealTimeCurrentRefAssignments(br: mechanicalsoup.stateful_browser.StatefulBrowser) -> dict:
    """
    Log into the MySoccerLeague website and pull all assignments for the weekend"""
    site = MySoccerLeague(br)
    assignments = site.getAssignments()
    return assignments


def getPastAssignments(br: mechanicalsoup.stateful_browser.StatefulBrowser, d: datetime.date) -> dict:
    site = MySoccerLeague(br)
    site.setSpecificDate(d)
    return site.getAssignments()


def getAllRefereesFromSite(br: mechanicalsoup.stateful_browser.StatefulBrowser) -> list:
    site = MySoccerLeague(br)
    return site.getAllReferees()


def getRefsAlreadyMentored() -> dict:
    """
    Pull the names of all referees already mentored this season
    """
    return db.getMentoringSessions()


def adjustDbNewRefs(inRefs: list) -> list:
    # convert from list of tuples to list of strings
    # [( 'martin', 'cooley')] -> [('martin cooley')]
    retVal = []
    for ref in inRefs:
        retVal.append(f'{ref[0]} {ref[1]}')
    return retVal


def getRiskyRefs() -> list:
    retVal = []
    refs = db.getRisky()
    for ref in refs:
        retVal.append(f'{ref[1]} {ref[0]}')
    return retVal


def generateWorkload(currentu: list, newRefs: list, mentored: list, risky: list) -> None:

    current = {}
    for c in sorted(currentu):
        current[c] = currentu[c]

    for field, details in current.items():
        fieldsOnce = False
        for game in details:

            center = details[game]['Center'].lower()
            ar1 = details[game]['AR1'].lower()
            ar2 = details[game]['AR2'].lower()

            if center not in newRefs and ar1 not in newRefs and ar2 not in newRefs:
                continue

            cmarker = '**' if center in mentored else ''
            a1marker = '**' if ar1 in mentored else ''
            a2marker = '**' if ar2 in mentored else ''

            crisky = '##' if center in risky else ''
            a1risky = '##' if ar1 in risky else ''
            a2risky = '##' if ar2 in risky else ''


            if not fieldsOnce:
                print("")
                print(f'Field: {field}')
                fieldsOnce = True

            date = details[game]['date']
            gameTime = details[game]['gameTime']
            age = details[game]['age']
            level = details[game]['level']

            print(f'\tID: {game}, Date: {date}, Time: {gameTime}, Age: {age}, Level: {level}')

            if center in newRefs:
                print(f'\t\tNew Ref at Center: {center.title()}{cmarker} {crisky}')

            if ar1 in newRefs:
                print(f'\t\tNew Ref at AR1: {ar1.title()}{a1marker} {a1risky}')

            if ar2 in newRefs:
                print(f'\t\tNew Ref at AR2: {ar2.title()}{a2marker} {a2risky}')

    print("")
    print("** Referee has already had a mentor")
    print("## Referee has been flagged as needing additional help")
    print("")


def run() -> None:

    """
    Make sure database is up-to-date with VYS new referee spreadsheet
    """
    latestRefs = getRefsFromGoogleSignupSheet()
    for ref in latestRefs:
        if not db.refExists(ref[0], ref[1]):
            db.addReferee(ref[0], ref[1], ref[2])

    """
    Verify new referees have the same first and last name in MSL.
    """
    newRefs = db.getNewReferees(2023)

    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]

    allRefs = getAllRefereesFromSite(br)

    # for ref in newRefs:
    #     if ref not in allRefs:
    #         print (f'Referee: {ref} not in MSL, check name spelling')

    # get this week's current assignments
    current = getRealTimeCurrentRefAssignments(br)

    # get list of already mentored referees
    mentored = getRefsAlreadyMentored()

    # get the list of risky refs (those needing to be seen again)
    risky = getRiskyRefs()

    # first adjust the format of data in newRefs from list of tuples
    # (firstname, lastname) to list of strings "firstname lastname"
    newRefs = adjustDbNewRefs(newRefs)

    generateWorkload(current, newRefs, mentored, risky)



if __name__ == "__main__":
    run()
