import streamlit as st
import time
from typing import Tuple

from database import RefereeDbCockroach
from uiData import getAllData


# get all the data we can, avoids a bunch of calls to the website
allMatchData = getAllData()
dates = list(allMatchData.keys())

db = RefereeDbCockroach()

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
if 'yearKey' not in st.session_state:
    st.session_state.yearKey = 'year'


def parseRefName(name: str) -> Tuple[str, str]:
    '''
    This handles all the idiosyncrasies of peoples names as configured
    in MSL.
    '''
    #st.write(f'refname: {name}')
    parts = name.split(',') # see "Michael Aguilera, Sr."
    #st.write(f'parts: {str(parts)}')
    if len(parts) > 1:
        return parts[0].split(' ')
    parts = name.split(' ')
    if len(parts) > 2:  # see 'Will Covey III'
        return (parts[0], parts[1])
    return parts

#----------------------------------------------------
# Specify the Mentor - mentors are pre-configured in the database
mentors = db.getMentors()

values = []
for mentor in mentors:
    entry = f'{mentor[0].capitalize()} {mentor[1].capitalize()}'
    values.append(entry)

st.selectbox("Please select a mentor", values, key='mentorKey')
#----------------------------------------------------


#----------------------------------------------------
# Specify the date - list of dates comes from MSL
st.selectbox("Please select the date of the match:", dates, key='dateKey')
dateInfo = st.session_state['dateKey']
#----------------------------------------------------


#----------------------------------------------------
# Specify the venue - venues come from MSL for the date selected
#matches = site.getMatches(st.session_state['dateKey'])
matches = allMatchData[st.session_state['dateKey']]
venues = list(matches.keys())
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


#----------------------------------------------------
def runReport() -> None:
    pass
#----------------------------------------------------


#----------------------------------------------------
# This handles the clicking of the Save button
# Save the mentor's comments for each of the selected
# referees

def doSave() -> None:
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
        status, message = db.addMentorSession(mentor,
                                              id[0].lower(), # referee
                                              id[1], # position
                                              st.session_state['dateKey'],
                                              st.session_state['comments'])
        if status:

            if len(refIds) == 1:
                st.balloons()

            # announce the good news
            box = st.success(message + f": Referee {id[0]}", icon="✅")

            # set up the timer for clearing the message
            time.sleep(5)
            box.empty()

            # reset the form
            formReset()

        else:
            st.error(f'There was some kind of error: {message}', icon="🚨")
#----------------------------------------------------


#----------------------------------------------------
# This handles the clicking of the Cancel button
# reset the form
def doCancel() -> None:
    formReset()
#----------------------------------------------------


#----------------------------------------------------
# Reset the form
def formReset() -> None:
    # To Do - set the date to the most reset date?
    # assuming this can be done

    st.session_state['comments'] = ''
    st.session_state['centercb'] = False
    st.session_state['ar1cb'] = False
    st.session_state['ar2cb'] = False

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
# Put some space in and add a button to run a report
# The report is a year-to-date

# Get the available years:
years = db.getYears()

# just put some space so it's not obvious
for _ in range(10):
    st.write("")

with st.container():
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("Get Report", on_click = runReport)
    with col2:
        st.write("Please select the year")
    with col3:
        st.selectbox("_", years, key='yearKey', label_visibility='collapsed')
#----------------------------------------------------
