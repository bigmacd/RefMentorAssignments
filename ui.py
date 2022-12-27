import mechanicalsoup
import os
import streamlit as st

from database import RefereeDbCockroach
from refWebSites import MySoccerLeague




br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
br.addheaders = [('User-agent', 'Chrome')]
site = MySoccerLeague(br)



def getMentor(mentors) -> None:

    values = []
    for mentor in mentors:
        entry = f'{mentor[0].capitalize()} {mentor[1].capitalize()}'
        values.append(entry)

    st.selectbox("Please select a mentor", values, key='mentor')


def getDate() -> None:
    dates = site.getAllDatesForSeason()
    st.selectbox("Please select the date of the match:", dates, key='date')


def getVenue(dateOfMatch: str) -> dict:
    matches = site.getMatches(dateOfMatch)
    venues = list(matches.keys())

    st.selectbox("Select the venue:", venues, key='venue')
    return matches


def getGames(matches: dict) -> None:
    # select a match
    games = matches[st.session_state['venue']]
    selectionList = []
    for game in games:
        selectionList.append(f"Time-{game['Time']}")
    st.selectbox("Which game?:", selectionList, key='game')


def getMatchDetails(matches: dict) -> None:
    game = st.session_state['game']
    gametime = game.split('-')[1]
    currentMatch = None
    for match in matches:
        if match['Time'] == gametime:
            currentMatch = match
    return currentMatch


def displayCrew(currentMatch: dict) -> None:

    with st.container():
        st.write("Please make a note in the comments if this crew is different!")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.button(f"Center: {currentMatch['Center']}", disabled=True)
        with col2:
            st.button(f"AR1: {currentMatch['AR1']}", disabled=True)
        with col3:
            st.button(f"AR2: {currentMatch['AR2']}", disabled=True)


def getComments() -> None:
    st.text_area("Comments", height=400, key="comments")


def doSave() -> None:
    pass


def doCancel() -> None:
    pass


def saveOrCancel() -> None:
    col1, _, col3 = st.columns(3)
    with col1:
        st.button("Save", on_click = doSave, key="save")
    # with col2:
    #     st.button(f"AR1: {currentMatch['AR1']}")
    with col3:
        st.button("Cancel", on_click = doCancel, key = "cancel")


def main() -> None:

    db = RefereeDbCockroach()
    mentors = db.getMentors()

    getMentor(mentors)
    getDate()
    matches = getVenue(st.session_state['date'])
    getGames(matches)
    currentMatch = getMatchDetails(matches[st.session_state['venue']])
    displayCrew(currentMatch)
    getComments()
    saveOrCancel()

if __name__ == "__main__":
    main()
