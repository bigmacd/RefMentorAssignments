import datetime
import os
import psycopg
import sqlite3
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


    def _getRange(self) -> list:
        # figure out if it is the fall or spring season.  Get reports for just that
        # range.
        today = datetime.datetime.today()
        year = today.year
        spring = [f'{year}-01-01', f'{year}-06-30']
        fall =   [f'{year}-07-01', f'{year}-12-31']
        return spring if today.month in (1, 2, 3, 4, 5, 6) else fall



    # finding stuff
    def refExists(self, lastname: str, firstname:str) -> bool:
        sql = "SELECT id from referees where lastname = %s and firstname = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return len(r.fetchall()) == 1


    def findReferee(self, lastname: str, firstname: str) -> list:
        sql = "SELECT * from referees where lastname = %s and firstname = %s"
        r = self.cursor.execute(sql, (lastname.lower(), firstname.lower()))
        return r.fetchone()


    def getReferees(self) -> list:
        sql = "SELECT firstname, lastname from referees"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def getNewReferees(self, year) -> list:
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


    def getMentoringSessions(self) -> dict:

        range = self._getRange()

        retVal = {}
        sql = f"select distinct r.lastname, r.firstname, ms.position, ms.date from mentor_sessions ms join referees r on ms.mentee = r.id where ms.date between '{range[0]}' and '{range[1]}'"
        print(sql)
        r = self.cursor.execute(sql)
        rows = r.fetchall()
        for row in rows:
            retVal[f'{row[1]} {row[0]}'] = [ row[2], row[3]]
        return retVal


    def getMentoringSessionDetails(self, year: int) -> dict:

        range = [f'{year}-01-01', f'{year}-12-31']
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where ms.date between '{range[0]}' and '{range[1]}' ORDER BY ms.date"
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

        dt = datetime.datetime.strptime(date, "%A, %B %d, %Y")

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


    def produceReport(self, year):

        retVal = ''
        sessions = self.getMentoringSessionDetails(year)
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

