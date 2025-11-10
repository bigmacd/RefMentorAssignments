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
            self.createDb()
        else:
            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='gamedetails'")
            if not self.cursor.fetchone()[0] == 1:
                self._createNewGameDetailTable()

            # for visitors, drop the old table and create the new one
            # old table is 'visitors'
            # new table is 'user_visits'
            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='visitors'")
            if self.cursor.fetchone()[0] == 1:
                self.cursor.execute(" DROP TABLE visitors")

            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='user_visits'")
            if not self.cursor.fetchone()[0] == 1:
                self._createUserVisitsTable()

            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='users'")
            if not self.cursor.fetchone()[0] == 1:
                self._createUsersTable()

            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='password_reset_tokens'")
            if not self.cursor.fetchone()[0] == 1:
                self._createPasswordResetTokensTable()

            self.cursor.execute(" SELECT count(table_name) FROM information_schema.tables WHERE table_schema LIKE 'public' AND table_type LIKE 'BASE TABLE' AND table_name='logs'")
            if not self.cursor.fetchone()[0] == 1:
                self._createLogsTable()

    def createDb(self) -> bool:

        sql = """CREATE TABLE referees (id SERIAL PRIMARY KEY,
                                        lastname TEXT NOT NULL,
                                        firstname TEXT NOT NULL,
                                        year_certified INTEGER)"""
        self.cursor.execute(sql)

        sql = """CREATE TABLE mentors (id SERIAL PRIMARY KEY,
                                        mentor_last_name TEXT NOT NULL,
                                        mentor_first_name TEXT NOT NULL)"""
        self.cursor.execute(sql)

        sql = """CREATE TABLE mentor_sessions (id SERIAL PRIMARY KEY,
                                                mentor INTEGER NOT NULL,
                                                mentee INTEGER NOT NULL,
                                                position TEXT NOT NULL,
                                                date TIMESTAMP NOT NULL,
                                                comments TEXT NOT NULL)"""
        self.cursor.execute(sql)

        sql = """CREATE TABLE risky (id SERIAL PRIMARY KEY,
                                     mentee INTEGER NOT NULL,
                                     mentor_session INTEGER NOT NULL,
                                     date TIMESTAMP NOT NULL DEFAULT NOW())"""
        self.cursor.execute(sql)

        self._createNewGameDetailTable()
        self._createUserVisitsTable()
        self._createUsersTable()
        self._createPasswordResetTokensTable()
        self._createLogsTable()


    def _createNewGameDetailTable(self):
            sql = """CREATE TABLE gamedetails ( id SERIAL PRIMARY KEY,
                                                venue TEXT NOT NULL,
                                                gameId TEXT NOT NULL,
                                                center TEXT NOT NULL,
                                                ar1 TEXT NOT NULL,
                                                ar2 TEXT NOT NULL,
                                                date text NOT NULL,
                                                time TEXT NOT NULL,
                                                age TEXT NOT NULL,
                                                level TEXT NOT NULL)"""
            self.cursor.execute(sql)


    def _createUserVisitsTable(self):
        sql = """CREATE TABLE user_visits (username TEXT NOT NULL,
                                           role TEXT NOT NULL,
                                           email TEXT NOT NULL,
                                           date TIMESTAMP NOT NULL DEFAULT NOW())"""
        self.cursor.execute(sql)


    def _createUsersTable(self):
        sql = """CREATE TABLE users (id SERIAL PRIMARY KEY,
                                     username TEXT UNIQUE NOT NULL,
                                     password_hash TEXT NOT NULL,
                                     salt TEXT NOT NULL,
                                     email TEXT UNIQUE NOT NULL,
                                     role TEXT NOT NULL DEFAULT 'user',
                                     created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                                     last_login TIMESTAMP)"""
        self.cursor.execute(sql)


    def _createPasswordResetTokensTable(self):
        sql = """CREATE TABLE password_reset_tokens (id SERIAL PRIMARY KEY,
                                                     user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                                     token TEXT UNIQUE NOT NULL,
                                                     expires_at TIMESTAMP NOT NULL,
                                                     created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                                                     used BOOLEAN NOT NULL DEFAULT FALSE)"""
        self.cursor.execute(sql)


    def _createLogsTable(self):
        sql = """CREATE TABLE logs (timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
                                    message TEXT NOT NULL)"""
        self.cursor.execute(sql)


    def addVisitor(self, email: str, username: str, role: str) -> None:
        sql = "INSERT INTO user_visits (email, username, role) values (%s, %s, %s)"
        self.cursor.execute(sql, (email, username, role))
        self.connection.commit()


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
        f, l = mentee.split(' ', 1)
        menteeId = self.findReferee(l, f)
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


    def getNewReferees(self) -> list:
        today = datetime.today()
        year = today.year
        sql = "SELECT firstname, lastname from referees where year_certified >= %s"
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


    def getMentoringSessionMetrics(self, year: int, season: str) -> dict:
        '''
        season is either 'fall' or 'spring'
        returns number of referees mentored and number of mentoring sessions
        '''

        def getRanges(season: str, year: int) -> list:
            if season == 'fall':
                return [f'{year}-07-01', f'{year}-12-31']
            else:
                return [f'{year}-04-01', f'{year}-06-30']

        range = getRanges(season, year)
        sql = f"""
            SELECT
            COUNT(DISTINCT ms.mentor) AS distinct_mentors,
            COUNT(DISTINCT ms.mentee) AS distinct_referees,
            COUNT(DISTINCT ms.id) AS distinct_reports
            FROM mentor_sessions ms
            WHERE ms.date BETWEEN '{range[0]}' AND '{range[1]}'
        """
        r = self.cursor.execute(sql)
        data =  r.fetchall()
        retVal = {
            'mentors': data[0][0],
            'referees': data[0][1],
            'reports': data[0][2]
        }
        return retVal


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
        firstname, lastname = referee.split(' ', 1)
        sql = f"select r.firstname, r.lastname, ms.position, ms.date, ms.comments, me.mentor_last_name, me.mentor_first_name \
              from mentor_sessions ms \
              join referees r on ms.mentee = r.id join mentors me on ms.mentor = me.id \
              where r.firstname = '{firstname.lower()}' and r.lastname = '{lastname.lower()}' \
              order by ms.date"
        r = self.cursor.execute(sql)
        return r.fetchall()


    def getMentoringsessionsForMentor(self, mentor: str) -> dict:
        # mentor string is like "David Helfgott"
        firstname, lastname = mentor.split(' ', 1)
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
        f, l = mentee.split(' ', 1)
        mentorId = self.findMentor(mentor.split(' ')[0], mentor.split(' ')[1])
        menteeId = self.findReferee(l, f)
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
        f, l = mentee.split(' ', 1)
        mentorId = self.findMentor(mentor.split(' ')[0], mentor.split(' ')[1])
        menteeId = self.findReferee(l, f)
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


    # The below was added so we can also track the game details

    def gameDetailsExist(self, gameId: str, date: str, time: str) -> bool:
        sql = "SELECT * from gamedetails where gameId = %s and date = %s and time = %s"
        try:
            self.cursor.execute(sql, (gameId, date, time))
        except Exception as ex:
            print(ex)
        return not self.cursor.fetchone() == None


    def addGameDetails(self, currentGames: dict) -> None:

        sql = """insert into gamedetails (venue,
                                    gameId,
                                    center,
                                    ar1,
                                    ar2,
                                    date,
                                    time,
                                    age,
                                    level)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""

        for venue, gameDetails in currentGames.items():
            for gameid, game in gameDetails.items():
                if 'VENUE CONFLICT' in gameid:
                    gameid = gameid.replace('VENUE CONFLICT', '')
                if self.gameDetailsExist(gameid, game['date'], game['gameTime']) is False:
                    self.cursor.execute(sql, (venue,
                                            gameid,
                                            game['Center'],
                                            game['AR1'],
                                            game['AR2'],
                                            game['date'],
                                            game['gameTime'],
                                            game['age'],
                                            game['level']))


    # User management methods for authentication

    def userExists(self, username: str) -> bool:
        """Check if a username already exists"""
        sql = "SELECT id FROM users WHERE username = %s"
        self.cursor.execute(sql, (username.lower(),))
        return self.cursor.fetchone() is not None


    def emailExists(self, email: str) -> bool:
        """Check if an email already exists"""
        sql = "SELECT id FROM users WHERE email = %s"
        self.cursor.execute(sql, (email.lower(),))
        return self.cursor.fetchone() is not None


    def createUser(self, username: str, password_hash: str, salt: str, email: str, role: str = 'user') -> None:
        """Create a new user"""
        sql = "INSERT INTO users (username, password_hash, salt, email, role) VALUES (%s, %s, %s, %s, %s)"
        self.cursor.execute(sql, (username.lower(), password_hash, salt, email.lower(), role))
        self.connection.commit()


    def getUserByUsername(self, username: str) -> dict:
        """Get user by username"""
        sql = "SELECT id, username, password_hash, salt, email, role, created_at, last_login FROM users WHERE username = %s"
        self.cursor.execute(sql, (username.lower(),))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'salt': row[3],
                'email': row[4],
                'role': row[5],
                'created_at': row[6],
                'last_login': row[7]
            }
        return None


    def getAllUsers(self) -> list:
        """Get all users"""
        sql = "SELECT id, username, email, role, created_at, last_login FROM users ORDER BY username"
        self.cursor.execute(sql)
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                'id': row[0],
                'username': row[1],
                'email': row[2],
                'role': row[3],
                'created_at': row[4],
                'last_login': row[5]
            })
        return users


    def updateUserPassword(self, username: str, password_hash: str, salt: str) -> None:
        """Update user password"""
        sql = "UPDATE users SET password_hash = %s, salt = %s WHERE username = %s"
        self.cursor.execute(sql, (password_hash, salt, username.lower()))
        self.connection.commit()


    def updateLastLogin(self, username: str) -> None:
        """Update user's last login time"""
        sql = "UPDATE users SET last_login = NOW() WHERE username = %s"
        self.cursor.execute(sql, (username.lower(),))
        self.connection.commit()


    def deleteUser(self, user_id: int) -> None:
        """Delete a user"""
        sql = "DELETE FROM users WHERE id = %s"
        self.cursor.execute(sql, (user_id,))
        self.connection.commit()


    def getUserByEmail(self, email: str) -> dict:
        """Get user by email address"""
        sql = "SELECT id, username, password_hash, salt, email, role, created_at, last_login FROM users WHERE email = %s"
        self.cursor.execute(sql, (email.lower(),))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'username': row[1],
                'password_hash': row[2],
                'salt': row[3],
                'email': row[4],
                'role': row[5],
                'created_at': row[6],
                'last_login': row[7]
            }
        return None


    def createPasswordResetToken(self, user_id: int, token: str, expires_at: datetime) -> None:
        """Create a password reset token"""
        # First, invalidate any existing tokens for this user
        sql = "UPDATE password_reset_tokens SET used = TRUE WHERE user_id = %s AND used = FALSE"
        self.cursor.execute(sql, (user_id,))

        # Create the new token
        sql = "INSERT INTO password_reset_tokens (user_id, token, expires_at) VALUES (%s, %s, %s)"
        self.cursor.execute(sql, (user_id, token, expires_at))
        self.connection.commit()


    def getPasswordResetToken(self, token: str, current_email: str) -> dict:
        """Get password reset token details"""
        sql = '''
          SELECT prt.id, prt.user_id, prt.token, prt.expires_at, prt.used, u.email, u.username
          FROM password_reset_tokens prt
          JOIN users u ON prt.user_id = u.id
          WHERE prt.token = %s AND prt.used = FALSE AND prt.expires_at > NOW() AND u.email = %s
        '''
        #self.cursor.execute('insert into logs (message) values (%s)', (f'Fetching token {token} for email {current_email}',))
        #self.cursor.execute("SELECT NOW()")
        #row = self.cursor.fetchone()
        #self.cursor.execute('insert into logs (message) values (%s)', (f'Current time is {row[0]}',))

        self.cursor.execute(sql, (token, current_email))
        row = self.cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'token': row[2],
                'expires_at': row[3],
                'used': row[4],
                'email': row[5],
                'username': row[6]
            }
        return None


    def getUsernameByResetToken(self, token: str) -> str:
        """Get username associated with a valid password reset token"""
        sql = "select u.email from password_reset_tokens prt JOIN users u on prt.user_id = u.id where prt.token = %s and prt.used = false and prt.expires_at < NOW()"
        self.cursor.execute(sql, (token,))
        row = self.cursor.fetchone()
        if row:
            return row[0]
        return None


    def usePasswordResetToken(self, token: str) -> None:
        """Mark a password reset token as used"""
        sql = "UPDATE password_reset_tokens SET used = TRUE WHERE token = %s"
        self.cursor.execute(sql, (token,))
        self.connection.commit()


    def cleanupExpiredTokens(self) -> None:
        """Remove expired password reset tokens"""
        sql = "DELETE FROM password_reset_tokens WHERE expires_at < NOW() OR used = TRUE"
        self.cursor.execute(sql)
        self.connection.commit()


    def logMessage(self, message: str) -> None:
        """Log a message to the logs table"""
        sql = "INSERT INTO logs (message) VALUES (%s)"
        self.cursor.execute(sql, (message,))
        self.connection.commit()


