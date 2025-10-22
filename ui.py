
import os
import uuid

from contextlib import contextmanager, redirect_stdout
from datetime import datetime as dtime
from io import StringIO
import streamlit as st
from streamlit_calendar import calendar

from streamlit_pills import pills
import time
from typing import Tuple

from database import RefereeDbCockroach
from excelWriter import getExcelFromText
from googleSheets import credFile
from auth import AuthManager, requireAuth, showUserManagement

from main import run
from uiData import getAllData


@contextmanager
def stCapture(outputFunc):
    with StringIO() as stdout, redirect_stdout(stdout):
        oldWrite = stdout.write

        def newWrite(string):
            ret = oldWrite(string)
            outputFunc(stdout.getvalue())
            return ret

        stdout.write = newWrite
        yield

st.set_page_config(layout='wide')

streamlitCloud = os.getenv('STREAMLIT_CLOUD', 'True')

if streamlitCloud == 'False':
    # Initialize authentication
    auth_manager = AuthManager()

    # Require authentication - this will show login form if not authenticated
    requireAuth(auth_manager)

    # Check if user management should be shown
    if st.session_state.get('show_user_management', False):
        showUserManagement(auth_manager)
        if st.button("← Back to Main App"):
            st.session_state.show_user_management = False
            st.rerun()
        st.stop()

# get all the data we can, avoids a bunch of calls to the website
allMatchData = getAllData()
dates = list(allMatchData.keys())

db = RefereeDbCockroach()

# Track authenticated user visits
if not streamlitCloud:
    if  auth_manager.getCurrentUser():
        db.addVisitor(auth_manager.getCurrentUser())
# else:
#     if st.user != "test@test.com":
#         db.addVisitor(st.user)

if 'mentor' not in st.session_state:
    st.session_state.mentor = 'mentor'
if 'date' not in st.session_state:
    st.session_state.date = 'date'
if 'gameKey' not in st.session_state:
    st.session_state.gameKey = 'gameKey'
if 'Center' not in st.session_state:
    st.session_state.Center = 'center'
if 'AR1' not in st.session_state:
    st.session_state.AR1 = 'ar1'
if 'AR2' not in st.session_state:
    st.session_state.AR2 = 'ar2'
if 'centercb' not in st.session_state:
    st.session_state.centercb = False
if 'ar1cb' not in st.session_state:
    st.session_state.ar1cb = False
if 'ar2cb' not in st.session_state:
    st.session_state.ar2cb = False
if 'revisitCenter' not in st.session_state:
    st.session_state.revisitCenter = False
if 'revisitAR1' not in st.session_state:
    st.session_state.revisitAR2 = False
if 'revisitAR2' not in st.session_state:
    st.session_state.revisitAR2 = False
if 'reportIndex' not in st.session_state:
    st.session_state.reportIndex = 0
if 'downloadButtonDisabled' not in st.session_state:
    st.session_state.downloadButtonDisabled = True
if 'centerMessageBox' not in st.session_state:
    st.session_state.centerMessageBox = None
if 'ar1MessageBox' not in st.session_state:
    st.session_state.ar1MessageBox = None
if 'ar2MessageBox' not in st.session_state:
    st.session_state.ar2MessageBox = None
if 'showButton' not in st.session_state:
    st.session_state.showButton = False
if 'reportRefereeSelection' not in st.session_state:
    st.session_state.reportRefereeSelection = ''
# if 'reportYearSelection' not in st.session_state:
#     st.session_state.reportYearSelection = None
if 'reportWeekSelection' not in st.session_state:
    st.session_state.reportWeekSelection = ''
if 'reportMentorSelection' not in st.session_state:
    st.session_state.reportMentorSelection = ''
# if 'dateKey' not in st.session_state:
#     st.session_state.dateKey = 'dates'

yearData = db.getYears()
yearData.insert(0, ' ')

#tab1, tab2, tab3 = st.tabs(['Main', 'Reports', 'Workload'])
tab = pills("Please select an activity", [
        "Enter a Mentor Report",
        "Generate Reports",
        "See Current Workload",
        "Calendar"
        ],
        ["📥", "📤", "📝", "🗓"])

#with tab1:
if tab == "Enter a Mentor Report":

    selectionBoxData = yearData

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


    #----------------------------------------------------
    # Specify the Mentor - mentors are pre-configured in the database
    mentors = db.getMentors()

    values = []
    for mentor in mentors:
        entry = f'{mentor[0].capitalize()} {mentor[1].capitalize()}'
        values.append(entry)
    values = sorted(values)
    st.selectbox("Please select a mentor", values, key='mentorKey')
    #----------------------------------------------------


    #----------------------------------------------------
    # Specify the date - list of dates comes from MSL
    dateIndex = getCurrentDateIndex(dates)
    if dates[dateIndex].startswith('Tuesday'):
        dateIndex = dateIndex + 1
    st.selectbox("Please select the date of the match:", dates, index=dateIndex, key='dateKey')
    dateInfo = st.session_state['dateKey']
    #----------------------------------------------------


    #----------------------------------------------------
    # Specify the venue - venues come from MSL for the date selected
    #matches = site.getMatches(st.session_state['dateKey'])
    matches = allMatchData[st.session_state['dateKey']]
    venues = list(matches.keys())
    venues = sorted(venues)
    st.selectbox("Select the venue:", venues, key='venue')
    #----------------------------------------------------


    #----------------------------------------------------
    # Specify which match - matches come from MSL for the date
    # and venue selected
    venueInfo = st.session_state['venue']
    games = matches[venueInfo]

    selectionList = []
    for game in games:
        selectionList.append(f"Time-{game['Time']}")
    st.selectbox("Which game?:", selectionList, key='game')

    game = st.session_state['game']
    gametime = game.split('-')[1]
    currentMatch = None

    for game in games:
        if game['Time'] == gametime:
            currentMatch = game
    #----------------------------------------------------


    #----------------------------------------------------
    # which referees are we mentoring?
    centerCB = None
    AR1CB = None
    AR2CB = None

    with st.container():
        st.write("Please select the new referees that were the focus of the mentoring:")
        col1, col2, col3 = st.columns(3)
        #disabled = False
        with col1:
            #disabled = True
            refname = currentMatch['Center']
            if refname != 'Not Used' and refname != 'None':
                fname, lname = parseRefName(refname)
            #    if db.findReferee(lname, fname):
            #        disabled = False
            centerCB = st.checkbox(f"Center: {currentMatch['Center']}", key='centercb')
        with col2:
            #disabled = True
            refname = currentMatch['AR1']
            if refname != 'Not Used' and refname != 'None':
                fname, lname = parseRefName(refname)
            #    if db.findReferee(lname, fname):
            #        disabled = False
            AR1CB = st.checkbox(f"AR1: {currentMatch['AR1']}", key='ar1cb')
        with col3:
            #disabled = True
            refname = currentMatch['AR2']
            if refname != 'Not Used' and refname != 'None':
                fname, lname = parseRefName(refname)
            #    if db.findReferee(lname, fname):
            #        disabled = False
            AR2CB = st.checkbox(f"AR2: {currentMatch['AR2']}", key='ar2cb')
    #----------------------------------------------------


    #----------------------------------------------------
    # Enter the comments from the mentor
    st.text_area("Comments", height=400, key="comments")
    #----------------------------------------------------


    def revisitCenterCB():
        if st.session_state.centerMessageBox is not None:
            st.session_state.centerMessageBox.empty()
        if centerCB is False:
            st.session_state.centerMessageBox = st.error("To request a revisit for center, the Center should be selected as a mentee", icon="🚨")
            st.session_state.revisitCenter = st.checkbox('Should Center be revisited?', on_change=revisitCenterCB, value = False)

    def revisitAR1CB():
        pass


    def revisitAR2CB():
        pass



    #----------------------------------------------------
    # Reset the form
    def formReset() -> None:
        # To Do - set the date to the most reset date?
        # assuming this can be done

        st.session_state['comments'] = ''
        st.session_state['centercb'] = False
        st.session_state['ar1cb'] = False
        st.session_state['ar2cb'] = False
        st.session_state['revisitCenter'] = False
        st.session_state['revisitAR1'] = False
        st.session_state['revisitAR2'] = False
        st.session_state.downloadButtonDisabled = True
    #----------------------------------------------------


    #----------------------------------------------------
    # Checkboxes to indicate if a referee should be revisted
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            revisitCenter = st.checkbox('Should Center be revisited?', key='revisitCenter')
        with col2:
            revisitAR1 = st.checkbox('Should AR1 be revisited?', key='revisitAR1', on_change=revisitAR1CB)
        with col3:
            revisitAR2 = st.checkbox('Should AR2 be revisited?', key='revisitAR2', on_change=revisitAR2CB)
    #----------------------------------------------------

    #----------------------------------------------------
    # This handles the clicking of the Cancel button
    # reset the form
    def doCancel() -> None:
        formReset()
    #----------------------------------------------------


    #----------------------------------------------------
    # This handles the clicking of the Save button
    # Save the mentor's comments for each of the selected
    # referees

    def doSave() -> None:

        global messagebox

        # get mentor
        mentor = st.session_state['mentorKey'].lower()

        # checkbox states - only report for refs that have been selected
        refs = [centerCB, AR1CB, AR2CB]
        position = ['Center', 'AR1', 'AR2']

        # tracks refs and the position they had
        refIds = []

        for i, ref in enumerate(refs):
            if ref is True:
                ref = currentMatch[position[i]]
                refIds.append((ref, position[i]))
        for id in refIds:
            # status, message = db.addMentorSession(mentor,
            #                                       id[0].lower(), # referee
            #                                       id[1], # position
            #                                       st.session_state['dateKey'],
            #                                       st.session_state['comments'])

            revisit = (id[1] == "Center" and st.session_state.revisitCenter is True) or \
            (id[1] == "AR1" and st.session_state.revisitAR1 is True) or \
            (id[1] == "AR2" and st.session_state.revisitAR2 is True)
            status, message = db.addMentorSessionNew(mentor,
                                                    id[0].lower(), # referee
                                                    id[1], # position
                                                    st.session_state['dateKey'],
                                                    st.session_state['comments'],
                                                    revisit)

            if status:

                if len(refIds) == 1:
                    st.balloons()

                # announce the good news
                #box = st.success(message + f": Referee {id[0]}", icon="✅")
                messagebox = st.success(message + f": Referee {id[0]}", icon="✅")

                # set up the timer for clearing the message
                time.sleep(5)
                messagebox.empty()
            else:
                st.error(f'There was some kind of error: {message}', icon="🚨")

        # reset the form
        formReset()
    #----------------------------------------------------


    #----------------------------------------------------
    # put the save and cancel buttons on the form
    col1, _, col3 = st.columns(3)
    with col1:
        st.button("Save", on_click = doSave, key="save")
    # with col2:
    #     st.button(f"AR1: {currentMatch['AR1']}")
    with col3:
        st.button("Cancel", on_click = doCancel, key = "cancel")

    #----------------------------------------------------


#with tab2:
elif tab == 'Generate Reports':

    def downloadClick():
        st.session_state.showButton = False

    #----------------------------------------------------
    def runByYearReport() -> None:
        year = st.session_state.reportYearSelection
        if year == ' ' or year is None:
            return
        st.session_state.showButton = True
    #----------------------------------------------------

    #----------------------------------------------------
    def runByWeekReport() -> None:
        week = st.session_state.reportWeekSelection
        if week == '' or week is None:
            return
        st.session_state.showButton = True
    #----------------------------------------------------

    #----------------------------------------------------
    def runByRefereeReport() -> None:
        referee = st.session_state.reportRefereeSelection
        if referee == '' or referee is None:
            return
        st.session_state.showButton = True
    #----------------------------------------------------

    #----------------------------------------------------
    def runByMentorReport() -> None:
        mentor = st.session_state.reportMentorSelection
        if mentor == '' or mentor is None:
            return
        st.session_state.showButton = True
    #----------------------------------------------------

    #----------------------------------------------------
    def runReport(reportType, reportFormat):
        st.session_state.showButton = True
        retVal = None
        if reportType == 'by year':
            if st.session_state.reportYearSelection == ' ' or st.session_state.reportYearSelection is None:
                st.session_state.showButton = False
            else:
                retVal = db.produceYearReport(st.session_state.reportYearSelection, reportFormat)
        elif reportType == 'by week':
            if st.session_state.reportWeekSelection == '' or st.session_state.reportWeekSelection is None:
                st.session_state.showButton = False
            else:
                retVal = db.produceWeekReport(st.session_state.reportWeekSelection, reportFormat)
        elif reportType == 'by referee':
            if st.session_state.reportRefereeSelection == '' or st.session_state.reportRefereeSelection is None:
                st.session_state.showButton = False
            else:
                retVal = db.produceRefereeReport(st.session_state.reportRefereeSelection, reportFormat)
        elif reportType == 'by mentor':
            if st.session_state.reportMentorSelection == '' or st.session_state.reportMentorSelection is None:
                st.session_state.showButton = False
            else:
                retVal = db.produceMentorReport(st.session_state.reportMentorSelection, reportFormat)

        if reportFormat == 'Text':
            return retVal
        else:
            getExcelFromText(retVal)
            with open('report.xlsx', 'rb') as fp:
                retVal = fp.read()
            return retVal
    #----------------------------------------------------

    #----------------------------------------------------
    format = st.radio("Select the report format:",
                      options = ['Text', 'Excel'],
                      index = 0,
                      disabled=False,
                      key="reportFormat")

    reportType = st.selectbox("Select the type of report",
                              options = ["by year", "by week", "by referee", "by mentor"],
                              key='reportType')

    if reportType == 'by year':
        st.empty()
        st.selectbox("Please select the year",
                    options=yearData,
                    key='reportYearSelection',
                    on_change=runByYearReport)
        st.empty()

    if reportType == 'by week':
        weeks = dates
        weeks.insert(0, '')
        st.empty()
        st.selectbox("Please select the week",
                     key='reportWeekSelection',
                     options = weeks,
                     on_change=runByWeekReport)
        st.empty()


    if reportType == 'by referee':
        st.empty()
        referees = db.getRefereesForSelectionBox()
        referees.insert(0, '')
        st.selectbox("Please select the referee",
                     key='reportRefereeSelection',
                     options = referees,
                     on_change=runByRefereeReport)


    if reportType == 'by mentor':
        st.empty()
        mentors = db.getMentorsForSelectionBox()
        mentors.insert(0, '')
        st.selectbox("Please select the mentor",
                     key='reportMentorSelection',
                     options = mentors,
                     on_change=runByMentorReport)


    empty = st.empty()
    if st.session_state.showButton:
        empty.download_button("Download Data",
                               data=runReport(reportType, format),
                               mime='text/plain' if st.session_state.reportFormat == 'Text' else 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                               on_click=downloadClick)
    #----------------------------------------------------

#with tab3:
elif tab == 'See Current Workload':

    skipKeys = ['mslUsername', 'mslPassword', 'db_url']
    # write the file needed by google auth from Streamlit secrets
    with open(credFile, 'w') as fp:
        fp.write('{\n')
        for k, v in st.secrets.items():

            if k in skipKeys:
                continue

            if k == 'private_key':
                v = v.encode('unicode_escape').decode('utf-8')

            fp.write(f'\t"{k}": "{v}"')

            if k != 'client_x509_cert_url':
                fp.write(',\n')
            else:
                fp.write('\n')
        fp.write('}')

    output = st.empty()
    with stCapture(output.code):
        run()

elif tab == "Calendar":

    event_to_add = {
        "title": "New Event",
        "start": "2024-09-01",
        "end": "2024-09-02",
        "resourceId": "a",
    }


    options = {
        "editable": True,
        "selectable": True,
        "initialView": "dayGridMonth",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,listMonth"
        }
    }

    if "CalendarKey" not in st.session_state:
        st.session_state["CalendarKey"] = str(uuid.uuid4())
    #events = [{"title": "Conference", "start": "2025-09-15", "end": "2025-09-17"}]
    cal_data = calendar(events=None, options=options, key="CalendarKey")

    # if st.button("Add Event"):
    #     events.append(event_to_add)
    #     #st.session_state["CalendarKey"] = str(uuid.uuid4())  # Refresh calendar
    #     st.rerun()  # Rerun app to reflect changes
