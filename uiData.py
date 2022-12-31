import mechanicalsoup
from typing import Tuple

from refWebSites import MySoccerLeague

initialized = False
allMatchData = None

def getAllData() -> Tuple[list, dict]:
    global initialized
    global dates
    global allMatchData

    if not initialized:
        # get all the data we can
        br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
        br.addheaders = [('User-agent', 'Chrome')]
        site = MySoccerLeague(br)
        dates = site.getAllDatesForSeason()

        allMatchData = {}
        for date in dates:
            allMatchData[date] = site.getMatches(date)

        initialized = True
    return allMatchData
