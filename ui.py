import mechanicalsoup
import streamlit as st

from database import RefereeDbCockroach
from refWebSites import MySoccerLeague


db = RefereeDbCockroach()
mentors = db.getMentors()


br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
br.addheaders = [('User-agent', 'Chrome')]
site = MySoccerLeague(br)



def getMentor() -> None:

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


def main() -> None:

    getMentor()
    getDate()

    matches = getVenue(st.session_state['date'])
    getGames(matches)
    currentMatch = getMatchDetails(matches[st.session_state['venue']])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.button(f"Center: {currentMatch['Center']}")
    with col2:
        st.button(f"AR1: {currentMatch['AR1']}")
    with col3:
        st.button(f"AR2: {currentMatch['AR2']}")

    # st.write("Please make a note in the comments if this crew is different!")


    # # enter comments


if __name__ == "__main__":
    main()
