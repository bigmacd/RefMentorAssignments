import os
import mechanicalsoup
import time

from argparse import ArgumentParser
from database import RefereeDbCockroach
from refWebSites import MySoccerLeague

if __name__ == "__main__":

    parser = ArgumentParser()
    parser.add_argument('--season', type=str, choices=['spring', 'fall', 'winter', 'all'], required=False, default='fall', help='Season to generate metrics for (spring or fall)')
    parser.add_argument('--year', type=int, required=False, default=time.localtime().tm_year, help='Year to generate metrics for (default: current year)')
    args = parser.parse_args()

    def getRanges(season: str, year: int) -> list:
        if season == 'fall':
            return [f'{year}-07-01', f'{year}-12-31']
        elif season == 'spring':
            return [f'{year}-04-01', f'{year}-06-30']
        elif season == 'winter':
            return [f'{year}-01-01', f'{year}-03-31']
        else:  # all
            return [f'{year}-01-01', f'{year}-12-31']

    startDate, endDate = getRanges(args.season, args.year)

    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    site = MySoccerLeague(br)
    metrics = site.getReportForSeason(startDate, endDate)

    # metrics
    # {'gamesPlayed': 452, 'totalRefAssignments': 944, 'refsAssigned': 908, 'refsMissing': 36, 'missingCenters': 0, 'missingARs': 36}

    reportMetrics = RefereeDbCockroach().getMentoringSessionMetrics(startDate, endDate)

    # reportMetrics
    # {'mentors': 5, 'referees': 31, 'reports': 52}
    print("MSL Metrics:")
    print(f"  Games Played: {metrics['gamesPlayed']}")
    print(f"  Total Ref Assignments: {metrics['totalRefAssignments']}")
    print(f"  Refs Assigned: {metrics['refsAssigned']}")
    print(f"  Refs Missing: {metrics['refsMissing']}")
    print(f"    Missing Centers: {metrics['missingCenters']}")
    print(f"    Missing ARs: {metrics['missingARs']}")
    print("Mentoring Metrics:")
    print(f"  Mentors: {reportMetrics['mentors']}")
    print(f"  Referees: {reportMetrics['referees']}")
    print(f"  Reports: {reportMetrics['reports']}")
