import os
import mechanicalsoup
import time

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


class MySoccerLeague(RefereeWebSite):

    def __init__(self, br, enddate: str):
        super(MySoccerLeague, self).__init__(br)
        self._baseUrl = self._loginPage = "https://mysoccerleague.com/YSLmobile.jsp"
        self._loginFormInput = { 'userName': os.environ['mslUsername'],
                                'password': os.environ['mslPassword'] }
        self.enddate = enddate

        for _ in range(3):
            try:
                self._login()
            except Exception:
                time.sleep(3)
            else:
                break


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


    def getReportData(self):
        url = f'https://mysoccerleague.com/GamesReportChoice.jsp?YSLkey={self._loginKey}&actionName=Game%20Reports'
        data = f'YSLkey={self._loginKey}&returnJsp=ShowGameReports.jsp&dateMode=allDates&startDate=2023-11-17&endDate=2023-11-17&ageGroupFilter=all&genderFilter=all&classFilter=all&grSelect=1&grSelect=2&grSelect=3&filterButton=View+Reports'
        data2 = {
            'YSLkey': self._loginKey,
            'returnJsp': 'ShowGameReports.jsp',
            'dateMode': 'allDates',
            'startDate': '2023-11-17',
            'endDate': '2023-11-17',
            'ageGroupFilter': 'all',
            'genderFilter': 'all',
            'classFilter': 'all',
            'grSelect': 1,
            'grSelect': 2,
            'grSelect': 3,
            'filterButton': 'View+Reports'
        }
        #response = requests.post(url, json = data2)
        self._browser.open(url)
        self._browser.select_form('form')
        self._browser['YSLkey'] = self._loginKey
        self._browser['returnJsp'] = 'ShowGameReports.jsp'
        self._browser['dateMode'] = 'allDates'
        response = self._browser.submit_selected()

        return response

    def getReportForSeason(self):
        reportData = self.getReportData()

        metrics = {
            "gamesPlayed": 0,
            "totalRefAssignments": 0,
            "refsAssigned": 0,
            "refsMissing": 0,
            "missingCenters": 0,
            "missingARs": 0
        }

        entries = reportData.soup.find_all("tr", { "class" : 'trstyle2' })

        metrics['gamesPlayed'] = len(entries)

        for entry in entries:
            elements = entry.find_all('td')

            refsNeeded = 3
            if elements[3].text == 'U-9' or elements[3].text == 'U-10':
                refsNeeded = 1
            metrics['totalRefAssignments'] += refsNeeded

            refsAssigned = 0
            ref1 = elements[8].text.strip('\xa0')
            ref2 = elements[9].text.strip('\xa0')
            ref3 = elements[10].text.strip('\xa0')

            if len(ref1) != 0:
                refsAssigned += 1
            else:
                metrics['missingCenters'] += 1

            if len(ref2) != 0:
                refsAssigned += 1
            else:
                if refsNeeded == 3:
                    metrics['missingARs'] += 1

            if len(ref3) != 0:
                refsAssigned += 1
            else:
                if refsNeeded == 3:
                    metrics['missingARs'] += 1

            metrics['refsAssigned'] += refsAssigned
            metrics['refsMissing'] += refsNeeded - refsAssigned


                #  0 <td>9/8/2023 - 9:30 PM</td>
                #  1 <td>764395 (confirmed)</td>
                #  2 <td><a href="javascript:directWindow('Oakton HS 3 - both sides','No directions available','No comments')">Oakton HS 3 Full field</a></td>
                #  3 <td>O-30</td>
                #  4 <td>Co-ed</td>
                #  5 <td>Rec</td>
                #  6 <td align="center">Team 4</td>
                #  7 <td align="center">Team 3</td>
                #  8 <td align="center">Jaime Villamarin</td>
                #  9 <td align="center">Martin Cooley</td>
                # 10 <td align="center">Jason Allen</td>

                #ref1 = elements[9].text.strip('\n').strip('\r')
                #ref2 = elements[10].text.strip('\n').strip('\r')
                #ref3 = elements[11].text.strip('\n').strip('\r')

        return metrics


if __name__ == "__main__":
    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    site = MySoccerLeague(br, '11/18/23')

    metrics = site.getReportForSeason()
    print(metrics)
