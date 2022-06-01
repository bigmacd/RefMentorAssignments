import os
import mechanicalsoup
import datetime
from datetime import timedelta


class RefereeWebSite(object):

    def __init__(self, br):
        self._browser = br
        self._baseUrl = None
        self._loginPage = None
        self._loginFormInput = None

    def baseUrl(self):
        return self._baseUrl

    def loginPage(self):
        return self._loginPage

    def loginFormInput(self):
        return self._loginFormInput

    def getLocationDetails(self, assignmentData):
        return None


class MySoccerLeague(RefereeWebSite):

    def __init__(self, br):
        super(MySoccerLeague, self).__init__(br)
        self._baseUrl = self._loginPage = "https://mysoccerleague.com/YSLmobile.jsp"
        self._loginFormInput = { 'userName': os.environ['mslUsername'],
                                'password': os.environ['mslPassword'] }
        self._dataItems = ['card',
                           'datetime',
                           'league',
                           'gamenumber',
                           'field',
                           'agegroup',
                           'gender',
                           'level',
                           'hometeam',
                           'awayteam'
                           'ref'
                           'assistant1',
                           'assistant2' ]
        self._login()
        self._getFutureDates()


    def _login(self):
        # The site we will navigate into, handling it's session
        self._browser.open(self._baseUrl)
        #print(self._browser.get_current_page())

        #login_page.raise_for_status()
        self._browser.select_form('form')
        #self._browser.get_current_form().print_summary()
        self._browser['userName'] = self._loginFormInput['userName']
        self._browser['password'] = self._loginFormInput['password']
        self._loginResponse = self._browser.submit_selected()
        self._loginKey = self._loginResponse.soup.find_all('a')[13]['href'].split('?')[1].split('&')[0].split('=')[1]


    def _getFutureDates(self):
        """
        Get the dates for the url for Friday, Saturday, and Sunday.
        """
        d = datetime.date.today()
        while d.weekday() != 4:  # Friday
            d += datetime.timedelta(1)

        self._friday = d.strftime('%m/%d/%Y')
        d += datetime.timedelta(1)
        self._saturday = d.strftime('%m/%d/%Y')
        d += datetime.timedelta(1)
        self._sunday = d.strftime('%m/%d/%Y')


    def _parseAssignments(self, assignments: list, results: dict, date: str) -> None:
        for a in assignments:
            elements = a.find_all('td')
            ref1 = elements[9].text
            ref2 = elements[10].text
            ref3 = elements[11].text
            field = elements[1].text
            level = elements[3].text
            gameTime = elements[2].text
            age = elements[4].text
            gameId = elements[0].text

            if ref1 in (' ', '\xa0', 'Not Used\n'):
                ref1 = 'None'
            if ref2 in (' ', '\xa0', 'Not Used\n'):
                ref2 = 'None'
            if ref3 in (' ', '\xa0', 'Not Used\n'):
                ref3 = 'None'
            if field not in results:
                results[field] = {}
            results[field][gameId] = {
                'Center': ref1,
                'AR1': ref2,
                'AR2': ref3,
                'date': date,
                'gameTime': gameTime,
                'age': age,
                'level': level
            }
            # if ref1 not in (' ', '\xa0', 'Not Used\n'):
            #     if ref1 not in results:
            #         results[ref1] = {}
            #     results[ref1][gameId] = { 'field': field, 'date': date, 'gameTime': gameTime, 'age': age, 'position': 'Center' }
            # if ref2 not in (' ', '\xa0', 'Not Used\n'):
            #     if ref2 not in results:
            #         results[ref2] = {}
            #     results[ref2][gameId] = { 'field': field, 'date': date, 'gameTime': gameTime, 'age': age, 'position': 'AR1' }
            # if ref3 not in (' ', '\xa0', 'Not Used\n'):
            #     if ref3 not in results:
            #         results[ref3] = {}
            #     results[ref3][gameId] = { 'field': field, 'date': date, 'gameTime': gameTime, 'age': age, 'position': 'AR2' }


    def getAssignments(self):
        try:
            results = {}

            # MSL url for current assignments
            # need to extract the key fom the login_result first
            url = "https://www.mysoccerleague.com/ViewRefAssignments.jsp?YSLkey={0}&seasonId=0&leagueId=91&dateMode=futureDates&date={1}&startDate=9/8/21&endDate=11/19/21".format(self._loginKey, self._friday)
            assignments_page = self._browser.open(url)
            rowtype1 = assignments_page.soup.find_all("tr", { "class" : 'trstyle1'})
            rowtype2 = assignments_page.soup.find_all("tr", { "class" : 'trstyle2'})
            assignments = rowtype1 + rowtype2

            self._parseAssignments(assignments, results, self._friday)

            url = "https://www.mysoccerleague.com/ViewRefAssignments.jsp?YSLkey={0}&seasonId=0&leagueId=91&dateMode=futureDates&date={1}&startDate=9/8/21&endDate=11/19/21".format(self._loginKey, self._saturday)
            assignments_page = self._browser.open(url)
            rowtype1 = assignments_page.soup.find_all("tr", { "class" : 'trstyle1'})
            rowtype2 = assignments_page.soup.find_all("tr", { "class" : 'trstyle2'})
            assignments = rowtype1 + rowtype2

            self._parseAssignments(assignments, results, self._saturday)

            url = "https://www.mysoccerleague.com/ViewRefAssignments.jsp?YSLkey={0}&seasonId=0&leagueId=91&dateMode=futureDates&date={1}&startDate=9/8/21&endDate=11/19/21".format(self._loginKey, self._sunday)
            assignments_page = self._browser.open(url)
            rowtype1 = assignments_page.soup.find_all("tr", { "class" : 'trstyle1'})
            rowtype2 = assignments_page.soup.find_all("tr", { "class" : 'trstyle2'})
            assignments = rowtype1 + rowtype2

            self._parseAssignments(assignments, results, self._sunday)

        except Exception as ex:
            print(ex)

        return results

