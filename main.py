from openpyxl import load_workbook
import csv
import mechanicalsoup
import os

from refWebSites import MySoccerLeague


def getRealTimeCurrentRefAssignments(br: mechanicalsoup.stateful_browser.StatefulBrowser) -> dict:
    """ 
    Log into the MySoccerLeague website and pull all assignments for the weekend"""
    site = MySoccerLeague(br)
    assignments = site.getAssignments()
    return assignments

def getNewReferees() -> dict:
    """
    Organize data from Dianne's spreadsheet of new referees.
    """
    results = {}
    # Open the Workbook
    workbook = load_workbook(filename = "Vys New Referees Fall 2021e.xlsx")
    sheet = workbook.active

    # Iterate the rows
    for row in sheet.iter_rows(min_row = 2):  

        lastName = row[0].value.lower().strip()
        firstName = row[1].value.lower().strip()
        attended = row[3].value

        if lastName == '':
            break

        results[f'{firstName} {lastName}'] = attended
    
    return results


def getAllReferees() -> dict:
    """
    Organize data from Dianne's MSL dump.
    """
    results = {}
    # Open the Workbook
    workbook = load_workbook(filename = "List of Referees as of September 21, 2021.xlsx")
    sheet = workbook.active

    # Iterate the rows
    for row in sheet.iter_rows(min_row = 2):  

        lastName = row[7].value.lower().strip()
        firstName = row[6].value.lower().strip()
        id = row[2].value

        if lastName == '':
            break

        results[f'{firstName} {lastName}'] = id
    
    return results


def getRefsFromReports() -> list:
    """
    Pull the names of all referees already mentored this season
    """
    retVal = []
    for x in os.listdir('reports'):
        if x.endswith(".xlsx"):
            workbook = load_workbook(filename = f'reports/{x}')
            sheet = workbook.active

            # Iterate the rows
            for i, row in enumerate(sheet.iter_rows(min_row = 2)):
                center = row[5].value

                if center == '' or center is None:
                    break

                center = center.lower().strip()
                retVal.append(center)

                ar1 = row[6].value
                if ar1 is not None and ar1 != 'n/a':
                    ar1 = ar1.lower().strip()
                    retVal.append(ar1)
                ar2 = row[7].value
                if ar2 is not None and ar1 != 'n/a':
                    ar2 = ar2.lower().strip()
                    retVal.append(ar2)

    return retVal


def printout(current: list, newRefs: list) -> None:
    # first print out all those with assignments
    for ref in newRefs:
        if ref not in current:
            continue
        print("")
        print(f'New Ref: {ref}')
        print('\tHas the following games scheduled:')
        games = current[ref]
        for id, game in games.items():
            field = game['field']
            gameTime = game['gameTime']
            age = game['age']
            position = game['position']
            date = game['date']
            print(f'\tID: {id}, Field: {field}, Date: {date}, Time: {gameTime}, Age: {age}, Position: {position}')
 
    # now print out all those without assignments
    for ref in newRefs:
        if ref not in current:
            print("")
            print(f'New Ref: {ref}')
            print("\tHas no games scheduled this week")


def printout2(currentu: list, newRefs: list, mentored: list) -> None:
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

            if not fieldsOnce:
                print("")
                print(f'Field: {field}')
                fieldsOnce = True

            date = details[game]['date']
            gameTime = details[game]['gameTime']
            age = details[game]['age']
            
            print(f'\tID: {game}, Field: {field}, Date: {date}, Time: {gameTime}, Age: {age}')

            cmarker = '**' if center in mentored else ''
            a1marker = '**' if ar1 in mentored else ''
            a2marker = '**' if ar2 in mentored else ''

            if center in newRefs:
                print(f'\t\tNew Ref at Center: {center.title()}{cmarker}')
            if ar1 in newRefs:
                print(f'\t\tNew Ref at AR1: {ar1.title()}{a1marker}')
            if ar2 in newRefs:
                print(f'\t\tNew Ref at AR2: {ar2.title()}{a2marker}')

    print("** Referee has already had a mentor")

def check() -> None:
    """
    Verify new referees have the same first and last name in MSL.
    """
    newRefs = getNewReferees()
    allRefs = getAllReferees()

    for ref in newRefs.keys():
        if ref not in allRefs:
            if ref == 'Mateo Stine':
                print('x')
            print (f'Referee: {ref} not in MSL, check name spelling')

def run() -> None:
    """"
    Gather the new referee data from Dianne and correlate with current week's assignment.
    """

    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]

    #current = getCurrentRefAssignments()
    current = getRealTimeCurrentRefAssignments(br)
    newRefs = getNewReferees()
    mentored = getRefsFromReports()

    #printout(current, newRefs)
    printout2(current, newRefs, mentored)



if __name__ == "__main__":
    run()
    #check()