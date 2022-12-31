import mechanicalsoup
import streamlit as st

from database import RefereeDbCockroach
from refWebSites import MySoccerLeague
from uiData import getAllData


# get all the data we can
# br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
# br.addheaders = [('User-agent', 'Chrome')]
# site = MySoccerLeague(br)
# dates = site.getAllDatesForSeason()

#allMatchData = {}
#for date in dates:
#    allMatchData[date] = site.getMatches(date)

allMatchData = getAllData()
dates = list(allMatchData.keys())

db = RefereeDbCockroach()

if 'mentor' not in st.session_state:
    st.session_state.mentor = 'mentor'
if 'date' not in st.session_state:
    st.session_state.date = 'date'
if 'gameKey' not in st.session_state:
    st.session_state.gameKey = 'gameKey'

mentors = db.getMentors()

values = []
for mentor in mentors:
    entry = f'{mentor[0].capitalize()} {mentor[1].capitalize()}'
    values.append(entry)

st.selectbox("Please select a mentor", values, key='mentorKey')

st.selectbox("Please select the date of the match:", dates, key='dateKey')

dateInfo = st.session_state['dateKey']

#matches = site.getMatches(st.session_state['dateKey'])
matches = allMatchData[st.session_state['dateKey']]

venues = list(matches.keys())

st.selectbox("Select the venue:", venues, key='venue')

# select a match

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

# for venue, matchdata in matches.items():
#     for match in matchdata:
#         if match['Time'] == gametime:
#             currentMatch = match

with st.container():
    st.write("Please make a note in the comments if this crew is different!")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.button(f"Center: {currentMatch['Center']}", disabled=True)
    with col2:
        st.button(f"AR1: {currentMatch['AR1']}", disabled=True)
    with col3:
        st.button(f"AR2: {currentMatch['AR2']}", disabled=True)


st.text_area("Comments", height=400, key="comments")


def doSave() -> None:
    db.addMentorSession()
    db.addMentorSession(st.session_state['mentor'])


def doCancel() -> None:
    pass


col1, _, col3 = st.columns(3)
with col1:
    st.button("Save", on_click = doSave, key="save")
# with col2:
#     st.button(f"AR1: {currentMatch['AR1']}")
with col3:
    st.button("Cancel", on_click = doCancel, key = "cancel")


