import argparse
import csv
import datetime
import mechanicalsoup
from openpyxl import load_workbook
import os
#from prompt_toolkit.shortcuts import radiolist_dialog, input_dialog, yes_no_dialog
from streamlit.web import cli as stcli
import sys

from database import RefereeDb
from refWebSites import MySoccerLeague

# def inputMentorReport():

#     done = False
#     while not done:
#         # start with mentors
#         db = RefereeDb()
#         mentors = db.getMentors()
#         values = []
#         for mentor in mentors:
#             entry = f'{mentor[0].capitalize()} {mentor[1].capitalize()}'
#             values.append((entry, entry))

#         mentor = radiolist_dialog(
#             values = values,
#             title = "Select Mentor",
#             text="Select a Mentor"
#         ).run()

#         # select referee
#         values = []
#         referees = db.getReferees()
#         for referee in referees:
#             entry = f'{referee[0].capitalize()} {referee[1].capitalize()}'
#             values.append((entry, entry))

#         referee = radiolist_dialog(
#             values = values,
#             title = "Select Referee",
#             text = "Select Referee"
#         ).run()

#         # select position
#         position = radiolist_dialog(
#             values = [
#                 ("Center", "Center"),
#                 ("AR1", "AR1"),
#                 ("AR2", "AR2")
#             ],
#             title = "Select Referee's Position",
#             text = "Select Referee's Position"
#         ).run()

#         # select date from list of dates for the season
#         br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
#         br.addheaders = [('User-agent', 'Chrome')]
#         m = MySoccerLeague(br)
#         dates = m.getAllDatesForSeason()

#         values = []
#         for date in dates:
#             values.append((date, date))

#         date = radiolist_dialog(
#             values = values,
#             title = "Select Date Mentored",
#             text = "Select Date Mentored"
#         ).run()

#         # input comments
#         comments = input_dialog(
#             title="Mentor Notes", text="Paste your comments here:"
#         ).run()

#         db.addMentorSession(mentor, referee, position, date, comments)

#         answer = yes_no_dialog(
#             title = "Add another mentor session?"
#         ).run()
#         if not answer: # the No button was pressed
#             done = True

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


def getNewReferees(filename: str) -> dict:
    """
    Organize data from Dianne's spreadsheet of new referees.
    """
    results = {}
    # Open the Workbook
    workbook = load_workbook(filename = filename)
    sheet = workbook.active

    # Iterate the rows
    for row in sheet.iter_rows(min_row = 2):

        if row[0].value == None:
            break

        lastName = row[0].value.lower().strip()
        firstName = row[1].value.lower().strip()
        attended = 0 #row[3].value

        if lastName == '':
            break

        results[f'{firstName} {lastName}'] = attended

    return results


def getNewRefereesFromGoogleSheet(filename: str) -> dict:
    results = {}

    # Open the Workbook
    workbook = load_workbook(filename = filename)
    sheet = workbook.active

    # Iterate the rows
    for row in sheet.iter_rows(min_row = 2):

        if row[0].value == None:
            break

        name = row[2].value.lower().strip()
        lastName, firstName = name.split(',')

        year = row[7].value.year

        if lastName == '':
            break

        results[f'{firstName.strip()} {lastName.strip()}'] = year

    return results



def getNewRefereesFromCSV(filename: str) -> dict:
    """
    Import Dianne's spreadsheet of new referees into CSV file.
    """
    results = {}
    # Open the file
    with open('newRefs/NewRefs2022Fall.csv') as fp:
        csvFile = csv.reader(fp)

        for row in csvFile:
            try:
                lastName = row[0].lower().strip()
                firstName = row[1].lower().strip()
            except IndexError:
                pass
            else:
                # hack this one name cuz MSL is bonk
                if firstName == "gabi":
                    firstName = "gabi "
                results[f'{firstName} {lastName}'] = 0

    return results


def getAllReferees() -> dict:
    """
    Organize data from Dianne's MSL dump.
    """
    results = {}
    # Open the Workbook
    workbook = load_workbook(filename = "newRefs/NewRefs10182022.xlsx")
    sheet = workbook.active

    # Iterate the rows
    index = 0
    for row in sheet.iter_rows(min_row = 2):

        lastName = row[7].value.lower().strip()
        firstName = row[6].value.lower().strip()
        id = row[2].value

        if index > 30 and lastName == '':
            break

        results[f'{firstName} {lastName}'] = id
        index += 1
    return results


def getRefsAlreadyMentored() -> dict:
    """
    Pull the names of all referees already mentored this season
    """
    db = RefereeDb()
    retVal = db.getMentoringSessions()

    return retVal


def getRefsAlreadyMentoredOld() -> list:
    """
    Pull the names of all referees already mentored this season
    """
    retVal = []
    for x in os.listdir('reports/fall2022'):
        # these filenames are firstname_lastname.txt
        if x.endswith(".txt"):
            filename = x.split('.')
            refName = filename[0].split('_')
            retVal.append(f'{refName[0].strip().lower()} {refName[1].strip().lower()}')
            # workbook = load_workbook(filename = f'reports/{x}')
            # sheet = workbook.active

            # # Iterate the rows
            # for i, row in enumerate(sheet.iter_rows(min_row = 2)):
            #     center = row[5].value

            #     if center == '' or center is None:
            #         break

            #     center = center.lower().strip()
            #     retVal.append(center)

            #     ar1 = row[6].value
            #     if ar1 is not None and ar1 != 'n/a':
            #         ar1 = ar1.lower().strip()
            #         retVal.append(ar1)
            #     ar2 = row[7].value
            #     if ar2 is not None and ar1 != 'n/a':
            #         ar2 = ar2.lower().strip()
            #         retVal.append(ar2)

    return retVal


def printout(currentu: list, newRefs: list, mentored: list, skip: bool, report: bool=False) -> None:
    current = {}
    for c in sorted(currentu):
        current[c] = currentu[c]

    if skip:
        print("Current Schedule of New Referees never mentored:")
    elif not report:
        print("Current Schedule of New Referees:")

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

            # only print out refs that are new and not previously mentored
            if skip and (center not in newRefs or cmarker == '**') \
                and (ar1 not in newRefs or a1marker == '**') \
                     and (ar2 not in newRefs or a2marker == '**'):
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

            if not (skip and cmarker == '**'):
                if center in newRefs:
            #if center in newRefs and cmarker != '**':
                    print(f'\t\tNew Ref at Center: {center.title()}{cmarker}')
            if not (skip and a1marker == '**'):
                if ar1 in newRefs:
            #if ar1 in newRefs and a1marker != '**':
                    print(f'\t\tNew Ref at AR1: {ar1.title()}{a1marker}')
            if not (skip and a2marker == '**'):
                if ar2 in newRefs:
            #if ar2 in newRefs and a2marker != '**':
                    print(f'\t\tNew Ref at AR2: {ar2.title()}{a2marker}')
    if not skip and not report:
        print("** Referee has already had a mentor")
    print("")

def check() -> None:
    """
    Verify new referees have the same first and last name in MSL.
    """
    newRefs = getNewRefereesFromGoogleSheet("newRefs/googlesheet.xlsx")
    allRefs = getAllReferees()

    for ref in newRefs.keys():
        if ref not in allRefs:
            print (f'Referee: {ref} not in MSL, check name spelling')


def updateDatabase(newRefs: dict):
    db = RefereeDb()
    for k, v in newRefs.items():
        first, last = k.split(" ")
        if not db.findReferee(last, first):
            db.addReferee(last, first, v)


def addMentors(db) -> None:
    mentors = [
        ("david", "helfgott"),
        ("david", "dunlap"),
        ("diane", "florkowski"),
        ("chuck", "o'reilly"),
        ("martin", "cooley")
    ]
    #db = RefereeDb()
    for item in mentors:
        if not db.mentorExists(item[0], item[1]):
            db.addMentor(item[0], item[1])


def run(skip: bool) -> None:
    """"
    Gather the new referee data from Dianne and correlate with current week's assignment.
    """
    # db maintenance for mentors
    addMentors()

    # Get the new refs from Google Sheet and make sure db is up-to-date
    newRefs = getNewRefereesFromGoogleSheet("newRefs/googlesheet.xlsx")
    updateDatabase(newRefs)

    # get this week's current assignments
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    current = getRealTimeCurrentRefAssignments(br)

    # get list of already mentored referees
    mentored = getRefsAlreadyMentored()

    #printout(current, newRefs)
    printout(current, newRefs, mentored, skip)
    printout(current, newRefs, mentored, not skip)


def produceReport() -> None:

    newRefs = getNewRefereesFromGoogleSheet("newRefs/googlesheet.xlsx")

    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    site = MySoccerLeague(br)
    dates = site.getAllDatesForSeason()
    today = datetime.date.today()
    todaysDate = datetime.datetime.combine(today, datetime.time(0, 0))
    assignments = []
    for date in dates:
        dt = datetime.datetime.strptime(date, "%A, %B %d, %Y")
        if dt < todaysDate:
            if dt.weekday() == 5: # Saturday
                site.setSpecificDate(dt)
                assignments.append(site.getAssignments())
    for a in assignments:
        printout(a, newRefs, [], False, True)


if __name__ == "__main__":

    from database import RefereeDbCockroach
    db = RefereeDbCockroach()
    addMentors(db)

    sys.argv = ['streamlit', 'run', '--server.port', '443', 'ui.py']
    stcli.main()

    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', dest='input', action='store_true', help='input a mentor report')
    parser.add_argument('-r', '--report', dest='report', action='store_true', help='run season report')

    args = parser.parse_args()
    if args.input:
        inputMentorReport()
    elif args.report:
        produceReport()
    else:
        check()
        run(skip = True)
