import base64
import os
import pickle
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class SendEmail():

    def __init__(self):
        # default to local proton bridge server
        self.mailserver = '127.0.0.1'
        self.serverPort = 1025

        self._username = os.environ.get('proton_bridge_username', None)
        self._password = os.environ.get('proton_bridge_password', None)
        self._you = None
        self._to = []
        self._subject = None
        self._body = None
        self._message = MIMEMultipart()


    def setFrom(self, you):
        self._message['From']= you


    def addRecipient(self, recipent):
        self._message['To'] = recipent


    def subject(self, subject):
        self._message['Subject'] = subject


    def message(self, message):
        self._body = message


    def send(self):
        with smtplib.SMTP(self.mailserver, self.serverPort) as pmbridge:
            pmbridge.starttls()
            pmbridge.login(self._username, self._password)

            self._message.attach(MIMEText(self._body, 'plain'))
            pmbridge.sendmail(self._message['From'], self._message['To'].split(','), self._message.as_string())


class GmailAPIEmail():

    def __init__(self):

        # Define Gmail API scope for sending email
        self.SCOPES = ['https://www.googleapis.com/auth/gmail.send']
        self.creds = None
        self.tokenfile = 'token.pickle'
        self.service = self.Authenticate()

    def Authenticate(self):

        # Run OAuth 2.0 flow to get credentials
        if os.path.exists(self.tokenfile):
            with open(self.tokenfile, 'rb') as token:
                creds = pickle.load(token)
        else:
            print("No token file found")
            return None
        # If no valid credentials, authenticate and save the token
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())  # Refresh access token automatically using the refresh token
            else:
                flow = InstalledAppFlow.from_client_secrets_file('gmailcreds.json', self.SCOPES)
                creds = flow.run_local_server(port=0)
            with open(self.tokenfile, 'wb') as token:
                pickle.dump(creds, token)
        # Build the Gmail API service
        return build('gmail', 'v1', credentials=creds)


    def send(self, _to: str, subject: str, message: str) -> None:

        if self.service is None:
            print("No Gmail service available, cannot send email")
        else:
            try:
                # Create email message
                msg = MIMEText(message)
                msg['to'] = _to
                msg['subject'] = subject

                # Encode the message in base64 format
                create_message = {'raw': base64.urlsafe_b64encode(msg.as_bytes()).decode()}

                # Send the email
                self.service.users().messages().send(userId='me', body=create_message).execute()

            except HttpError as error:
                print(f'An error occurred: {error}')


if __name__ == '__main__':

    # g = SendEmail()
    # g.setFrom('someuser@gmail.com')
    # g.addRecipient('someuser@gmail.com')
    # g.subject("Do you want to be a milli?")
    # g.message("test message")
    # g.send()

    g = GmailAPIEmail()
    g.send('someuser@some.org', 'test subject', 'test message')

