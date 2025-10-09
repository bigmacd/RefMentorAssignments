from nicegui import ui

from uiData import getMatchData, getMentors, getCurrentDateIndex, getVenues
from uiData import getGames, getReferees

from nicegui import ui

alldata = getMatchData()
dates = list(alldata.keys())
mentors = getMentors()
currentData = getCurrentDateIndex(dates)

with ui.tabs().classes('w-full') as tabs:
    one = ui.tab('Enter a Mentor Report')
    two = ui.tab('Generate a Report')
    three = ui.tab('See Current Workload')
with ui.tab_panels(tabs, value=one).classes('w-full'):

    # Enter a mentor report
    with ui.tab_panel(one):
        with ui.column():

            ui.label('Please select a mentor')
            mentor = ui.select(mentors, value=mentors[0])

            ui.label("Please select the date of the match")
            date = ui.select(dates, value=dates[currentData])

            ui.label("Please select the venue")
            venues = getVenues(alldata, date.value)
            venue = ui.select(venues, value=venues[0])

            ui.label("Please select the game")
            games = getGames(venue.value, date.value)
            game = ui.select(games, value=games[0])

            ui.label("Please indicate the new referees that were the focus of the mentoring")
            refs = getReferees(game.value)
            with ui.row().style('width: 100%'):
                centercb = ui.checkbox(f"Center: {refs[0]}")
                ar1cb = ui.checkbox(f"AR1: {refs[1]}")
                ar2cb = ui.checkbox(f"AR2: {refs[2]}")

            #ui.label("Comments")
            comments = ui.textarea(label="Comments",
                        placeholder="")
            comments.style('width: 100%')


    with ui.tab_panel(two):
        ui.label('Second tab')
    with ui.tab_panel(three):
        ui.label("Third")
ui.run()



ui.run()

