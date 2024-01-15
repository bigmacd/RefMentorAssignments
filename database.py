from datetime import datetime, timedelta
import os
import psycopg
from typing import Tuple


class RefereeDbCockroach(object):

    def __init__(self):
        self.connection = psycopg.connect(os.environ['db_url'])
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()
        self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='referees'")
        if not self.cursor.fetchone()[0] == 1:
            self.createDb(self.cursor)


    def createDb(self, cursor) -> bool:

        sql = """CREATE TABLE referees (id SERIAL PRIMARY KEY,
                                        lastname TEXT NOT NULL,
                                        firstname TEXT NOT NULL,
                                        year_certified INTEGER)"""
        cursor.execute(sql)

        sql = """CREATE TABLE mentors (id SERIAL PRIMARY KEY,
                                        mentor_last_name TEXT NOT NULL,
                                        mentor_first_name TEXT NOT NULL)"""
        cursor.execute(sql)

        sql = """CREATE TABLE mentor_sessions (id SERIAL PRIMARY KEY,
                                                mentor INTEGER NOT NULL,
                                                mentee INTEGER NOT NULL,
                                                position TEXT NOT NULL,
                                                date TIMESTAMP NOT NULL,
                                                comments TEXT NOT NULL)"""
        cursor.execute(sql)

        sql = """CREATE TABLE risky (id SERIAL PRIMARY KEY,
                                     mentee INTEGER NOT NULL,
                                     mentor_session INTEGER NOT NULL,
                                     date TIMESTAMP NOT NULL DEFAULT NOW())"""
        cursor.execute(sql)


    def _getRiskRange(self) -> list:
        today = datetime.today()

        oneMonthAgo = today - timedelta(days=31)
        return [oneMonthAgo, today]


    def _getSeasonRange(self) -> list:
        # figure out if it is the fall or spring season.  Get reports for just that
        # range.
        today = datetime.today()
        year = today.year
        spring = [f'{year}-01-01', f'{year}-06-30']
        fall =   [f'{year}-07-01', f'{year}-12-31']
        return spring if today.month in (1, 2, 3, 4, 5, 6) else fall


    def _removeRisky(self, mentee: str):
        menteeId = self.findReferee(mentee.split(' ')[1], mentee.split(' ')[0])
        menteeId = 1
        sql = f"DELETE FROM risky WHERE mentee = '{menteeId}'"
        self.cursor.execute(sql)


    # finding stuff

    def isRisky(self, lastname: str, firstname: str) -> bool:

        # get today's date and look into the risky table from today back one month
        # if the referee is in the risky table, return true

        range = self._getRiskRange()

        mentee = self.findReferee(lastname, firstname)
        if mentee is None:
            return False

        menteeId = mentee[0]

        sql = f"SELECT * FROM risky WHERE mentee = {menteeId} and date between '{range[0]}' and '{range[1]}'"
        r = self.cursor.execute(sql)

        return len(r.fetchall()) > 0


    def getRisky(self) -> list:
        range = self._getRiskRange()

        sql = f"SELECT lastname, firstname from referees r where r.id in (SELECT mentee from risky where date between '{range[0]}' and '{range[1]}')"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def refExists(self, lastname: str, firstname:str) -> bool:
        sql = "SELECT id from referees where lastname = %s and firstname = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return len(r.fetchall()) == 1


    def findReferee(self, lastname: str, firstname: str) -> list:
        sql = "SELECT * from referees where lastname = %s and firstname = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return r.fetchone()


    def getReferees(self) -> list:
        # retrieve only the referees that have reports
        # return the list in sorted by last name order
        def lastname(item):
            return item[1]

        sql = "select distinct firstname, lastname from referees r join mentor_sessions ms on ms.mentee = r.id"
        r = self.cursor.execute(sql)
        data = r.fetchall()
        return sorted(data, key=lastname)


    def getRefereesForSelectionBox(self) -> list:
        refs = self.getReferees()
        retVal = []
        for ref in refs:
            retVal.append(f'{ref[0].capitalize()} {ref[1].capitalize()}')
        return retVal


    def getMentorsForSelectionBox(self) -> list:
        mentors = self.getMentors()
        retVal = []
        for mentor in mentors:
            retVal.append(f'{mentor[0].capitalize()} {mentor[1].capitalize()}')
        return retVal


    def getNewReferees(self, year) -> list:
        today = datetime.today()
        year = today.year
        sql = "SELECT firstname, lastname from referees where year_certified = %s"
        r = self.cursor.execute(sql, (year,))
        return r.fetchall()


    def mentorExists(self, firstname: str, lastname:str) -> bool:
        sql = "SELECT id from mentors where mentor_last_name = %s and mentor_first_name = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return len(r.fetchall()) == 1


    def findMentor(self, firstname: str, lastname: str) -> list:
        sql = "SELECT * from mentors where mentor_last_name = %s and mentor_first_name = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return r.fetchone()


    def getMentors(self) -> list:
        sql = "SELECT mentor_first_name, mentor_last_name from mentors"
        r = self.cursor.execute(sql)
        return r.fetchall()


    # def getMentoringSessions(self) -> dict:

    #     range = self._getSeasonRange()

    #     retVal = {}
    #     sql = f"select distinct r.lastname, r.firstname, ms.position, ms.date from mentor_sessions ms join referees r on ms.mentee = r.id where ms.date between '{range[0]}' and '{range[1]}'"
    #     r = self.cursor.execute(sql)
    #     rows = r.fetchall()
    #     for row in rows:
    #         retVal[f'{row[1]} {row[0]}'] = [ row[2], row[3]]
    #     return retVal


    def getMentoringSessions(self) -> dict:

        range = self._getSeasonRange()

        retVal = {}
        # sql = f"select r.lastname, r.firstname, ms.position from mentor_sessions ms join referees r on ms.mentee = r.id where ms.date between '{range[0]}' and '{range[1]}'"
        sql = f"select r.lastname, r.firstname, ms.position from mentor_sessions ms join referees r on ms.mentee = r.id"
        r = self.cursor.execute(sql)
        rows = r.fetchall()
        for row in rows:
            key = f'{row[1]} {row[0]}'
            if key not in retVal:
                retVal[key] = []
            retVal[key].append(row[2])
        return retVal


    def getMentoringSessionDetails(self, year: int) -> dict:

        range = [f'{year}-01-01', f'{year}-12-31']
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where ms.date between '{range[0]}' and '{range[1]}' ORDER BY ms.date"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def getMentoringsessionsForWeek(self, week: str) -> dict:
        # week string is like "Friday, April 14, 2023"
        d = datetime.strptime(week, "%A, %B %d, %Y")
        dt = d.strftime("%Y-%m-%d")
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where ms.date = '{dt}'"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def getMentoringsessionsForReferee(self, referee: str) -> dict:
        # referee string is like "Kate Curby"
        firstname, lastname = referee.split(' ')
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where r.firstname = '{firstname.lower()}' and r.lastname = '{lastname.lower()}' \
              order by ms.date"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def getMentoringsessionsForMentor(self, mentor: str) -> dict:
        # mentor string is like "David Helfgott"
        firstname, lastname = mentor.split(' ')
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where me.mentor_first_name = '{firstname.lower()}' and me.mentor_last_name = '{lastname.lower()}' \
              order by ms.date"
        r = self.cursor.execute(sql)
        return r.fetchall()

    def getYears(self) -> list:
        retVal = []
        sql = 'SELECT DISTINCT date from mentor_sessions'
        r = self.cursor.execute(sql)
        data = r.fetchall()
        for d in data:
            if d[0].year not in retVal:
                retVal.append(d[0].year)
        return retVal


    # adding data
    def setIsRisky(self, mentee: int, mentorSession: int, dt: datetime):
        sql = "INSERT into risky (mentee, mentor_session, date) \
               VALUES (%s, %s, %s)"
        self.cursor.execute(sql, (mentee, mentorSession, dt))
        self.connection.commit()


    def addReferee(self, lastname: str, firstname: str, year: int):
        sql = "INSERT INTO referees (lastname, firstname, year_certified) \
               VALUES (%s, %s, %s)"
        self.cursor.execute(sql, (lastname, firstname, year))
        self.connection.commit()


    def addMentor(self, firstname: str, lastname: str) -> None:
        sql = "INSERT INTO mentors (mentor_last_name, mentor_first_name) \
               VALUES (%s, %s)"
        self.cursor.execute(sql, (lastname, firstname))
        self.connection.commit()


    def addMentorSession(self,
                         mentor: str,
                         mentee: str,
                         position: str,
                         date: str,
                         comments: str) -> Tuple[bool, str]:
        sql = 'INSERT INTO mentor_sessions (mentor, mentee, position, date, comments) \
               VALUES (%s, %s, %s, %s, %s)'
        mentorId = self.findMentor(mentor.split(' ')[0], mentor.split(' ')[1])
        menteeId = self.findReferee(mentee.split(' ')[1], mentee.split(' ')[0])
        if mentorId is None:
            return (False, f'Could not find mentor details for {mentor}')
        if menteeId is None:
            return (False, f'Could not find referee details for {mentee}')

        dt = datetime.strptime(date, "%A, %B %d, %Y")

        try:
            self.cursor.execute(sql,
                                [mentorId[0],
                                menteeId[0],
                                position,
                                dt,
                                comments])
        except Exception as ex:
            return (False, f'Failed to add mentor report: {ex}')
        else:
            self.connection.commit()
            return (True, "Mentor Report successfully submitted!")


    def addMentorSessionNew(self,
                            mentor: str,
                            mentee: str,
                            position: str,
                            date: str,
                            comments: str,
                            isRisky: bool) -> Tuple[bool, str]:
        if not isRisky:
            self._removeRisky(mentee)
            return self.addMentorSession(mentor, mentee, position, date, comments)


        sql = 'INSERT INTO mentor_sessions (mentor, mentee, position, date, comments) \
               VALUES (%s, %s, %s, %s, %s) RETURNING id'
        mentorId = self.findMentor(mentor.split(' ')[0], mentor.split(' ')[1])
        menteeId = self.findReferee(mentee.split(' ')[1], mentee.split(' ')[0])
        if mentorId is None:
            return (False, f'Could not find mentor details for {mentor}')
        if menteeId is None:
            return (False, f'Could not find referee details for {mentee}')

        dt = datetime.strptime(date, "%A, %B %d, %Y")

        try:
            self.cursor.execute(sql,
                                [mentorId[0],
                                menteeId[0],
                                position,
                                dt,
                                comments])
            newId = self.cursor.fetchone()[0]

        except Exception as ex:
            return (False, f'Failed to add mentor report: {ex}')
        else:
            self.connection.commit()
            self.setIsRisky(menteeId[0], newId, dt)
            return (True, "Mentor Report successfully submitted!")

    def _getTextFromSessions(self, sessions):
        retVal = ''
        # [0] is firstname, [1] is lastname, [2] is position
        # [3] is date and [4] is comments
        sessionData = {}

        for session in sessions:
            date = session[3]
            if date not in sessionData: # session[3] is date
                sessionData[date] = []

            sessionData[date].append(
                {
                    'ref': f'{session[0].capitalize()} {session[1].capitalize()}',
                    'position': session[2],
                    'mentor': f'{session[6].capitalize()} {session[5].capitalize()}',
                    'comments': session[4]
                })

        # build a big `ol string to returned as a download`
        for k, entries in sessionData.items():
            retVal += f'Date: {k}\r\n'
            for entry in entries:
                retVal += f"\tReferee: {entry['ref']}\r\n"
                retVal += f"\tPosition: {entry['position']}\r\n"
                retVal += f"\tMentor: {entry['mentor']}\r\n"
                retVal += f"\tComments: {entry['comments']}\r\n\r\n"

        return retVal


    def produceYearReport(self, year, reportType):
        sessions = self.getMentoringSessionDetails(year)
        return self._getTextFromSessions(sessions)


    def produceWeekReport(self, week, reportType):
        sessions = self.getMentoringsessionsForWeek(week)
        return self._getTextFromSessions(sessions)


    def produceRefereeReport(self, referee, reportType):
        for name in referee:
            name.lower()
        sessions = self.getMentoringsessionsForReferee(referee)
        return self._getTextFromSessions(sessions)


    def produceMentorReport(self, mentor, reportType):
        sessions = self.getMentoringsessionsForMentor(mentor)
        return self._getTextFromSessions(sessions)
