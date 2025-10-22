import argparse
import datetime
from datetime import timedelta, datetime
import mechanicalsoup
import os


from database import RefereeDbCockroach
from refWebSites import MySoccerLeague
from googleSheets import getRefsFromGoogleSignupSheet


db = RefereeDbCockroach()

def getRealTimeCurrentRefAssignments(br: mechanicalsoup.stateful_browser.StatefulBrowser) -> dict:
    """
    Log into the MySoccerLeague website and pull all assignments for the weekend"""
    site = MySoccerLeague(br)
    site.setSpecificDate(datetime.now() - timedelta(days=1))
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

    minimizeOutput = os.environ.get('MINIMIZE_OUTPUT', 'false').lower() == 'true'

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

            cmarker = ''
            if center in mentored and 'Center' in mentored[center]:
                cmarker = '**'
            a1marker = ''
            if ar1 in mentored and ('AR1' in mentored[ar1] or 'AR2' in mentored[ar1]):
                a1marker = '**'
            a2marker = ''
            if ar2 in mentored and ('AR2' in mentored[ar2] or 'AR1' in mentored[ar2]):
                a2marker = '**'
            # cmarker = '**' if center in mentored else ''
            # a1marker = '**' if ar1 in mentored else ''
            # a2marker = '**' if ar2 in mentored else ''

            crisky = '##' if center in risky else ''
            a1risky = '##' if ar1 in risky else ''
            a2risky = '##' if ar2 in risky else ''



            # trying to reduce output a bit
            # if the crew is new and has already been mentored (but not flagged as needed follow-up), skip
            if minimizeOutput:
                if center in newRefs:
                    if cmarker == '**' and crisky == '':
                        newRefs.remove(center)
                if ar1 in newRefs:
                    if a1marker == '**' and a1risky == '':
                        newRefs.remove(ar1)
                if ar2 in newRefs:
                    if a2marker == '**' and a2risky == '':
                        newRefs.remove(ar2)
                if center not in newRefs and ar1 not in newRefs and ar2 not in newRefs:
                    continue



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

    # adding this line to try to fix the deployment on streamlit.app
    db = RefereeDbCockroach()

    """
    Make sure database is up-to-date with VYS new referee spreadsheet
    """
    latestRefsFromSpreadsheet = getRefsFromGoogleSignupSheet()
    # returns list of tuples (lastname, firstname, year_certified)

    for ref in latestRefsFromSpreadsheet:
        if not db.refExists(ref[0], ref[1]):
            print(f"{ref[1].capitalize()} {ref[0].capitalize()} not in database, adding")
            db.addReferee(ref[0], ref[1], ref[2])

    """
    Retrieve referees from MSL
    """
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]

    allRefsFromMSL = getAllRefereesFromSite(br)
    # return list of tuples (firstname, lastname)

    # This was a one-time thing?
    # """
    # Update database with MSL referee list
    # """
    # for ref in allRefs:
    #     if not db.refExists(ref[1], ref[0]):
    #         print(f"missing ref: {ref[1]} {ref[0]}") #db.addReferee(ref[1], ref[0], 2000)

    """
    Verify new referees have the same first and last name in MSL.
    """
    newRefs = db.getNewReferees()
    # returns list of tuples (firstname, lastname)

    for ref in newRefs:
         if ref not in allRefsFromMSL:
             print (f'Referee: {ref[0]} {ref[1]} not in MSL, check name spelling')

    # get this week's current assignments
    current = getRealTimeCurrentRefAssignments(br)
    db.addGameDetails(current)

    # get list of already mentored referees
    mentored = getRefsAlreadyMentored()

    # get the list of risky refs (those needing to be seen again)
    risky = getRiskyRefs()

    # first adjust the format of data in newRefs from list of tuples
    # (firstname, lastname) to list of strings "firstname lastname"
    newRefs = adjustDbNewRefs(newRefs)

    generateWorkload(current, newRefs, mentored, risky)


def getEmails():
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    site = MySoccerLeague(br)
    _ = site.getAllReferees()
    return site.emails



if __name__ == "__main__":
    bademails = [
        os.environ.get('badmentor1'),
        os.environ.get('badmentor2'),
        os.environ.get('badmentor3')
    ]
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', action="store_true")
    args = parser.parse_args()
    if args.e is True:
        emails = getEmails()
        emails = sorted(emails)
        print(f"Retrieved {len(emails)} email addresses from MSL")
        for x, email in enumerate(emails):
            if email in bademails:
                continue
            print(email)
    else:
        run()
