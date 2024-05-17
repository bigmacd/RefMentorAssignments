import argparse
import datetime
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


def generateWorkload(currentu: list,
                     newRefs: list,
                     mentored: list,
                     risky: list) -> None:

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


            if not fieldsOnce:
                print("")
                print(f'Field: {field}')
                fieldsOnce = True

            date = details[game]['date']
            gameTime = details[game]['gameTime']
            age = details[game]['age']
            level = details[game]['level']

            print(f'    ID: {game}, Date: {date}, Time: {gameTime}, Age: {age}, Level: {level}')

            if center in newRefs:
                print(f'        New Ref at Center: {center.title()}{cmarker} {crisky}')

            if ar1 in newRefs:
                print(f'        New Ref at AR1: {ar1.title()}{a1marker} {a1risky}')

            if ar2 in newRefs:
                print(f'        New Ref at AR2: {ar2.title()}{a2marker} {a2risky}')

    print("")
    print("** Referee has already had a mentor")
    print("## Referee has been flagged as needing additional help")
    print("")


def generateNewWorkload(currentu: list,
                        newRefs: list,
                        mentored: list,
                        risky: list) -> dict:
    buffer = {}

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

            if field not in buffer:
                buffer[field] = {}

            buffer[field][game] = []

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

            if not fieldsOnce:
                buffer[field][game].append('')
                buffer[field][game].append(f'Field: {field}')
                fieldsOnce = True

            date = details[game]['date']
            gameTime = details[game]['gameTime']
            age = details[game]['age']
            level = details[game]['level']

            buffer[field][game].append(f'    ID: {game}, Date: {date}, Time: {gameTime}, Age: {age}, Level: {level}')

            if center in newRefs:
                buffer[field][game].append(f'        New Ref at Center: {center.title()}{cmarker} {crisky}')

            if ar1 in newRefs:
                buffer[field][game].append(f'        New Ref at AR1: {ar1.title()}{a1marker} {a1risky}')

            if ar2 in newRefs:
                buffer[field][game].append(f'        New Ref at AR2: {ar2.title()}{a2marker} {a2risky}')

    return buffer


def run(newWorkload: bool = False) -> None:

    # adding this line to try to fix the deployment on streamlit.app
    db = RefereeDbCockroach()

    """
    Make sure database is up-to-date with VYS new referee spreadsheet
    """
    latestRefs = getRefsFromGoogleSignupSheet()
    # returns list of tuples (lastname, firstname, year_certified)

    for ref in latestRefs:
        if not db.refExists(ref[0], ref[1]):
            print(f"{ref[1].capitalize()} {ref[0].capitalize()} not in database, adding")
            db.addReferee(ref[0], ref[1], ref[2])

    """
    Retrieve referees from MSL
    """
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]

    allRefs = getAllRefereesFromSite(br)
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
         if ref not in allRefs:
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

    if not newWorkload:
        generateWorkload(current, newRefs, mentored, risky)
    else:
        return generateNewWorkload(current, newRefs, mentored, risky)


def getEmails():
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    site = MySoccerLeague(br)
    _ = site.getAllReferees()
    return site.emails


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', action="store_true")
    args = parser.parse_args()
    if args.e is True:
        emails = getEmails()
        numEmails = len(emails)
        half = numEmails/2
        once = False
        for x, email in enumerate(emails):
            if email == os.environ.get('badmentor1') or email == os.environ.get('badmentor2'):
                continue
            if x >= half and once is False:
                for _ in range(0, 5):
                    print("")
                    once = True
            print(email)
    else:
        run()
