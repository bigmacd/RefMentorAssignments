import os
import datetime
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

    def getLocationDetails(self, assignmentData):
        return None


class MySoccerLeague(RefereeWebSite):

    def __init__(self, br):
        super(MySoccerLeague, self).__init__(br)
        self._baseUrl = self._loginPage = "https://mysoccerleague.com/YSLmobile.jsp"
        self._loginFormInput = { 'userName': os.environ['mslUsername'],
                                'password': os.environ['mslPassword'] }

        for _ in range(3):
            try:
                self._login()
            except Exception as ex:
                time.sleep(3)
            else:
                break
        self._getFutureDates(datetime.date.today())
        self.emails = []


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


    def _getFutureDates(self, d: datetime.date):
        """
        Get the dates for the url for Friday, Saturday, and Sunday.
        """
        while d.weekday() != 4:  # Friday
            d += datetime.timedelta(1)

        self._friday = d.strftime('%m/%d/%Y')
        d += datetime.timedelta(1)
        self._saturday = d.strftime('%m/%d/%Y')
        d += datetime.timedelta(1)
        self._sunday = d.strftime('%m/%d/%Y')


    def setSpecificDate(self, d: datetime.date) -> None:
        # Allows us to go back in time and produce the mentor workload report
        self._getFutureDates(d)


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


    def getAllDatesForSeason(self) -> list:
        url = "https://mysoccerleague.com/ViewRefAssignments.jsp?YSLkey={0}&seasonId=0&leagueId=91&dateMode=allDates".format(self._loginKey)

        page = self._browser.open(url)
        box = page.soup.find("td", { "class" : 'tblborderforms', 'align' : 'center' })
        dates = box.find_all("a")
        results = []
        # skip the first two entries
        for i in range(2, len(dates)):
            results.append(dates[i].text.strip())
        return results


    def getMatches(self, dateInfo: str) -> dict:
        url = 'https://www.mysoccerleague.com/ViewRefAssignments.jsp?YSLkey={0}&seasonId=0&leagueId=91&dateMode=allDates&date={1}'

        # convert from 'Day, Month Date, Year' i.e. (Saturday, September 24, 2022)
        # to m/d/year
        parts = dateInfo.split(',')
        year = parts[2]
        month, day = parts[1].lstrip().split(' ')

        # fix month
        dateObject = datetime.datetime.strptime(f'{month} {day} {year}', '%B %d %Y')
        convertedDate = f'{dateObject.month}/{dateObject.day}/{dateObject.year}'

        url = url.format(self._loginKey, convertedDate)
        page = self._browser.open(url)

        entries1 = page.soup.find_all("tr", { "class" : 'trstyle1' })
        entries2 = page.soup.find_all("tr", { "class" : 'trstyle2' })

        entries = entries1 + entries2

        '''
        Each entry is like this:  Organize by venue.

        <tr class="trstyle1">
        <td align="center">748590<br/><font color="green"></font></td>
        <td><a href="javascript:directWindow('Ken Lawrence #2','No directions available','No comments')">Ken Lawrence #2</a></td>
        <td>8:00 AM</td>
        <td>U12G House</td>
        <td>U-12</td>
        <td>Girls</td>
        <td>Rec</td>
        <td>Bill Chappell</td>
        <td>Katie Cohen</td>
        <td align="left">Danika Pfleghardt</td>
        <td align="left">Mitra Tafreshi</td>
        <td align="left">Kate Curby</td>
        </tr>'''

        retVal = {}

        for entry in entries:
            elements = entry.find_all('td')
            ref1 = elements[9].text.strip('\n').strip('\r')
            ref2 = elements[10].text.strip('\n').strip('\r')
            ref3 = elements[11].text.strip('\n').strip('\r')

            # clean up the ref data as MSL can make a mess of it
            if ref1 in (' ', '\xa0', 'Not Used\n'):
                ref1 = 'None'
            if ref2 in (' ', '\xa0', 'Not Used\n'):
                ref2 = 'None'
            if ref3 in (' ', '\xa0', 'Not Used\n'):
                ref3 = 'None'

            field = elements[1].text.strip().strip('\n').strip('\r')
            level = elements[3].text
            gameTime = elements[2].text
            age = elements[4].text
            gameId = elements[0].text


            if field not in retVal:
                retVal[field] = []

            data = {
                'Center': ref1.replace('[VYS]', ''),
                'AR1': ref2.replace('[VYS]', ''),
                'AR2': ref3.replace('[VYS]', ''),
                'Time': gameTime,
                'Level' :level,
                'Age': age,
                'GameID' :gameId
            }
            retVal[field].append(data)

        return retVal


    def getAssignments(self):
        for _ in range(3):
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

            except Exception:
                time.sleep(3)
            else:
                break

        return results

    def getAllReferees(self) -> list:
        emails = None
        retVal = None
        for _ in range(3):
            try:
                url = 'https://www.mysoccerleague.com/AddRef.jsp?YSLkey={0}&actionName=Referees&showAll=true'.format(self._loginKey)
                print(f"checking {url}")
                page = self._browser.open(url)

                entries1 = page.soup.find_all("tr", { "class" : 'trstyle1' })
                entries2 = page.soup.find_all("tr", { "class" : 'trstyle2' })

                entries = entries1 + entries2

                retVal = []
                emails = []
                for entry in entries:
                    elements = entry.find_all('td')
                    refereeFullName = elements[4].text
                    emails.append(elements[7].text)
                    try:
                        firstName, lastName = refereeFullName.split(' ')
                    except ValueError:
                        f, l, x = refereeFullName.split(' ')
                        # handle weirdness in MSL (three part names, extra spaces, etc.)

                        last = None

                        if f == 'Alexandre':
                            if l == 'de':
                                last = l + ' ' + x
                        elif f == 'Will':
                            if l == 'Covey' and x == 'III':
                                last = l + ' ' + x
                        elif f == 'Gabriella':
                            if l == '(Brie)':
                                last = l + ' ' + x
                        elif f == 'Sophie':
                            if x == 'Hinton':
                                last = x
                        elif f == 'Vivienne':
                            if x == 'Huang':
                                last = x
                        elif f == 'Andrew':
                            if x == 'Teale':
                                last = x
                        elif f == 'Gabi':
                            if x == 'Konde':
                                last = x
                        elif f == 'James':
                            if x == 'Horn':
                                last = f"{l} {x}"
                        elif f == 'Joseph':
                            if x == 'Sandoval':
                                last = f"{l} {x}"
                            elif x == 'Howe':
                                last = f"{l} {x}"
                        elif f == 'Mohamed':
                            if l == 'Nour':
                                last = f"{l} {x}"
                        elif f == 'Jack':
                            if x == 'Raaphorst':
                                last = f"{l} {x}"
                        elif f == 'Laith':
                            if x == 'Habri':
                                last = f"{l} {x}"
                        elif f == 'William':
                            if l == 'Covey,':
                                if x == 'Jr':
                                    l = l.strip(',')
                                    last = f"{l} {x}"
                        elif f == 'Sofia':
                            if l == 'Velasquez':
                                last = f"{l} {x}"
                        elif f == 'Martiel':
                            if l == 'Ruiz':
                                last = f"{l} {x}"
                        elif f == 'Michael':
                            if l == 'Aguilera':
                                if x == 'Jr':
                                    last = f"{l} {x}"
                        elif f == 'Mary':
                            if l == 'Kate':
                                f = f"{f} {l}"
                                last = x
                        else:
                            print(f'Error parsing: {refereeFullName}: f: {f} l: {l}, x:{x}')

                        if last is None:
                            print(f'Error parsing: {refereeFullName}: f: {f} l: {l}, x:{x}')
                        else:
                            retVal.append((f.lower().strip(), last.lower().strip()))


                    retVal.append((firstName.lower().strip(), lastName.lower().strip()))

            except Exception:
                time.sleep(3)
            else:
                break
        self.emails = emails
        return retVal

