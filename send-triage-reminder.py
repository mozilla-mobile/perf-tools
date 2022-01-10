# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

"""To use this script:
1. Get .google-credentials.json file
2. Run! e.g. `python3 triage-reminder 2022-01-10 <email> <email> <email>`
"""

# TODO: share access to cloud project with others.
# TODO: figure out how to share secrets (move to web app?).

import argparse
import re
import os.path
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# 'Performance Team' calendar ID.
ID_CALENDAR = 'mozilla.com_9bk5f2rqdeuip38jbeld84kpqc@group.calendar.google.com'

PATH_SECRETS = '.google-credentials.json'
PATH_TOKEN = '.google-token.json'

DESCRIPTION = '''{} as Triage Sheriff #1 this week, can you please take the lead to coordinate a date/time this week?

For the latest bug nominations, please use https://mzl.la/2SySJtj.'''


def parse_args():
    # TODO: make args nice.
    parser = argparse.ArgumentParser()
    parser.add_argument('date', help='the date of the reminder. Format="yyyy-mm-dd"')
    parser.add_argument('email', help="email addresses of triage participants", nargs='+')
    return parser.parse_args()


def validate_args(args):
    # TODO: can further protect by only allowing year/month/day +/-1
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    if not date_pattern.match(args.date):
        print('ERROR: provided date does not match expected format. Expected: "yyyy-mm-dd"', file=sys.stderr)
        sys.exit(1)

    num_emails = len(args.email)
    if num_emails != 3:
        print('WARNING: expected 3 emails for triage: got {}.'.format(num_emails), file=sys.stderr)


# via https://developers.google.com/calendar/api/quickstart/python
def auth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(PATH_TOKEN):
        creds = Credentials.from_authorized_user_file(PATH_TOKEN, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(PATH_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open(PATH_TOKEN, 'w') as token:
            token.write(creds.to_json())
    return creds


# via https://developers.google.com/calendar/api/quickstart/python
def get_calendar_service(creds):
    try:
        return build('calendar', 'v3', credentials=creds)
    except HttpError as error:
        print('Unable to fetch calendar service: {}'.format(error), file=sys.stderr)
        raise error


def send_triage_reminder(service, date, emails):
    attendees = [{'email': email} for email in emails]
    description = DESCRIPTION.format(emails[0])

    event = {
        'summary': 'Reminder: perf triage rotation',
        'description': description,
        'start': {
            'dateTime': '{}T17:00:00Z'.format(date),  # utc.
        },
        'end': {
            'dateTime': '{}T17:30:00Z'.format(date),  # utc.
        },
        'attendees': attendees,

        # TODO: is this working? I don't think I can test it on myself.
        'sendNotifications': True,  # send an "Invitation: ..." email to attendees.
    }

    try:
        event = service.events().insert(calendarId=ID_CALENDAR, body=event).execute()
        print('Event created: {}'.format(event.get('htmlLink')))
    except HttpError as error:
        print('Error when creating event: {}'.format(error), file=sys.stderr)


def main():
    args = parse_args()
    validate_args(args)

    creds = auth()
    service = get_calendar_service(creds)
    send_triage_reminder(service, args.date, args.email)


if __name__ == '__main__':
    main()
