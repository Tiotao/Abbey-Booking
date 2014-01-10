#  #### ##     ## ########   #######  ########  ######## 
#   ##  ###   ### ##     ## ##     ## ##     ##    ##    
#   ##  #### #### ##     ## ##     ## ##     ##    ##    
#   ##  ## ### ## ########  ##     ## ########     ##    
#   ##  ##     ## ##        ##     ## ##   ##      ##    
#   ##  ##     ## ##        ##     ## ##    ##     ##    
#  #### ##     ## ##         #######  ##     ##    ##    

# General
import os
import httplib2
import sys
import datetime
import json
import urllib
import urllib2
import requests
from dateutil import parser
from rfc3339 import rfc3339

#Thread
import thread
from decorators import async

# Google
import gspread
import gdata.spreadsheet.service
from apiclient.discovery import build
from oauth2client.client import SignedJwtAssertionCredentials
from oauth2client.file import Storage
from config import SERVICE_MAIL, GROUP_MAIL, ADMIN_MAIL, APPROVED_CAL_ID, PERMIT_ID, PERMIT_VALIDATE, ADMIN_VALIDATE, PENDING_CAL_ID, DEVELOPER_ID, SPREADSHEET_ACC, SPREADSHEET_PW, SPREADSHEET_ID, LOG_KEY 

# Flask
from flask.ext.openid import OpenID
from flask.ext.mail import Mail, Message
from flask_oauth import OAuth
from flask import Flask, request, render_template, session, url_for, redirect, flash, send_from_directory, g


#   ######   #######  ##    ## ######## ####  ######   
#  ##    ## ##     ## ###   ## ##        ##  ##    ##  
#  ##       ##     ## ####  ## ##        ##  ##        
#  ##       ##     ## ## ## ## ######    ##  ##   #### 
#  ##       ##     ## ##  #### ##        ##  ##    ##  
#  ##    ## ##     ## ##   ### ##        ##  ##    ##  
#   ######   #######  ##    ## ##       ####  ######   

# App
app = Flask(__name__)
app.config.from_object('config')
basedir = os.path.abspath(os.path.dirname(__file__))

# Mail
mail=Mail(app)

# OpenID
oid = OpenID(app, os.path.join(basedir, 'tmp'))


#   ######   #######  ##    ## ######## ########   #######  ##       ##       ######## ########  
#  ##    ## ##     ## ###   ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
#  ##       ##     ## ####  ##    ##    ##     ## ##     ## ##       ##       ##       ##     ## 
#  ##       ##     ## ## ## ##    ##    ########  ##     ## ##       ##       ######   ########  
#  ##       ##     ## ##  ####    ##    ##   ##   ##     ## ##       ##       ##       ##   ##   
#  ##    ## ##     ## ##   ###    ##    ##    ##  ##     ## ##       ##       ##       ##    ##  
#   ######   #######  ##    ##    ##    ##     ##  #######  ######## ######## ######## ##     ##

# HELPER

# format the datetime to rfc3339
def get_start_end_rfc3339(dt):

    apptTime = dt.split()
    apptDate = apptTime[0]
    apptStartTime = apptTime[1]
    apptEndTime = apptTime[2]
    apptTimeZone = apptTime[3]
    start_datetime = datetime.datetime.strptime(apptStartTime, '%H:%M%p').time()
    start_formatted = start_datetime.strftime("%I:%M%p")
    end_datetime = datetime.datetime.strptime(apptEndTime, '%H:%M%p').time()
    end_formatted = end_datetime.strftime("%I:%M%p")
    apptDateObject = datetime.datetime.strptime(apptDate, '%m/%d/%Y').date()
    apptStartTimeObject = datetime.datetime.strptime(apptStartTime, '%I:%M%p').time()
    apptEndTimeObject = datetime.datetime.strptime(apptEndTime, '%I:%M%p').time()
    start_combined = datetime.datetime.combine(apptDateObject, apptStartTimeObject)
    end_combined = datetime.datetime.combine(apptDateObject, apptEndTimeObject)
    start_time = start_combined.strftime("%Y-%m-%dT%H:%M:00")
    end_time = end_combined.strftime("%Y-%m-%dT%H:%M:00")

    start_dt_rfc3339 = datetime_combine_rfc3339(apptDateObject, apptStartTimeObject)
    end_dt_rfc3339 = datetime_combine_rfc3339(apptDateObject, apptEndTimeObject)

    json = {
        'start' : start_time,
        'end' : end_time,
        'timezone' : apptTimeZone,
        'startdt' : start_dt_rfc3339,
        'enddt' : end_dt_rfc3339
    }

    return json

# function to turn strings of date and time into rfc3339 format for Google Calendar API call
# returns string of datetime in rfc339 format
def datetime_combine_rfc3339(date, time):
    combined = datetime.datetime.combine(date, time)
    rfc3339_datetime = rfc3339(combined)
    SGT = "+08:00"
    rfc3339_datetime = rfc3339_datetime[:-6] + SGT
    return rfc3339_datetime

# function to generate list of suggested free dates for user to choose from
def generate_date_list(startdate, enddate, starttime, endtime, calendarid):
    apptStartDate = datetime.datetime.strptime(startdate, '%Y-%m-%d').date()
    apptStartTime = datetime.datetime.strptime(starttime, '%H:%M').time()
    apptEndDate = datetime.datetime.strptime(enddate, '%Y-%m-%d').date()
    apptEndTime = datetime.datetime.strptime(endtime, '%H:%M').time()
    # td used to increment while loop one day at a time (24 hours)
    td = datetime.timedelta(hours=24)
    # store user's requested start time for use in while loop
    current_date = apptStartDate
    # empty list to store suggested free dates
    free_dates = []

    #authorization
    service = authorize()

    # loop from user's requested start date to end date
    while current_date <= apptEndDate:
        # format start and end times for Google Calendar API call
        start_rfc3339 = datetime_combine_rfc3339(current_date, apptStartTime)
        print start_rfc3339
        end_rfc3339 = datetime_combine_rfc3339(current_date, apptEndTime)

        print end_rfc3339
        event_list = service.events().list(calendarId=APPROVED_CAL_ID, timeMin=start_rfc3339, timeMax=end_rfc3339).execute()['items']
        event_list.extend(service.events().list(calendarId=PENDING_CAL_ID, timeMin=start_rfc3339, timeMax=end_rfc3339).execute()['items'])
        print "o:", event_list
        # if there are no events given back, then that time is empty
        # add date to the suggested free time list
        if not event_list:
            free_dates.append(current_date)
        # if the length of the free_dates array has reached 5, then break from loop
        if len(free_dates) == 5:
            break
        # increment current_date by 1 day to continue while loop
        current_date += td
    return free_dates

# convert json to list
def json_to_list(json, keys):
    lst = []
    for key in keys:
        lst.append(json[key])
    return lst


# GOOGLE CALENDAR
# get available calendars
def get_pending_cal():
    service = authorize()
    pending_cal = service.calendarList().get(calendarId=PENDING_CAL_ID).execute()
    return pending_cal

# get available pending events in a list
def get_pending_events():
    service = authorize()
    events = service.events().list(calendarId=PENDING_CAL_ID).execute()['items']
    pending_events = []
    for e in events:
        j = created_event_to_json(e)
        pending_events.append(j)

    return pending_events

# create service objects for google calendar
def authorize():
    f = file('key.p12', 'rb')
    key = f.read()
    f.close()
    credentials = SignedJwtAssertionCredentials(DEVELOPER_ID,
                                                key,
                                                scope='https://www.googleapis.com/auth/calendar')
    http = httplib2.Http()
    http = credentials.authorize(http)

    service = build("calendar", "v3", http=http)

    return service


# GOOGLE SPREADSHEET
# update json to spreadsheet
@async
def to_spreadsheet(json):
    gc = gspread.login(SPREADSHEET_ACC, SPREADSHEET_PW)
    wks = gc.open_by_key(SPREADSHEET_ID).sheet1
    wks.append_row(json_to_list(json, LOG_KEY))

# get details of a booking from spreadsheet
def fetch_from_spreadsheet(eid):
    gc = gspread.login(SPREADSHEET_ACC, SPREADSHEET_PW)
    wks = gc.open_by_key(SPREADSHEET_ID).sheet1
    row_no = wks.find(eid).row
    value = wks.row_values(row_no)
    json = dict(zip(LOG_KEY, value))
    return json

def validate_permit_from_spreadsheet(matric):
    if PERMIT_VALIDATE is False:
        return True
    else:
        gc = gspread.login(SPREADSHEET_ACC, SPREADSHEET_PW)
        wks = gc.open_by_key(PERMIT_ID).sheet1
        try: 
            row = wks.find(matric)
            return True
        except gspread.GSpreadException:
            return False

def validate_admin_from_spreadsheet(matric):
    if ADMIN_VALIDATE is False:
        return True
    else:
        gc = gspread.login(SPREADSHEET_ACC, SPREADSHEET_PW)
        wks = gc.open_by_key(PERMIT_ID).worksheets()[1]
        try: 
            row = wks.find(matric)
            return True
        except gspread.GSpreadException:
            return False
    

# update a log in spreadsheet when a booking gets approved
@async
def update_spreadsheet(newid, eid, status):
    json = fetch_from_spreadsheet(eid)
    json['id'] = newid
    json['status'] = status
    json['approved_time'] = str(datetime.datetime.now())
    gc = gspread.login(SPREADSHEET_ACC, SPREADSHEET_PW)
    wks = gc.open_by_key(SPREADSHEET_ID).sheet1
    value = json_to_list(json, LOG_KEY)
    try:
        row_no = wks.find(eid).row
        for i in range(0, len(value)):
            wks.update_cell(row_no, i+1, value[i])
    except gspread.exceptions.CellNotFound:
        wks.append_row(value)


# EMAIL
# send confirmation email
@async
def send_approve_mail(event, email_address):
    with app.test_request_context():
        msg = Message(
                'Your Booking is approved',
                sender= SERVICE_MAIL,
                recipients=[email_address])
        msg.body = render_template("confirmation_email.txt", 
            event=event)
        msg.html = render_template("confirmation_email.html", 
            event=event)
        mail.send(msg)
        
@async
def send_alert_mail(event, email_address):
    with app.test_request_context():
        msg = Message(
                'New booking waiting for approval',
                sender= SERVICE_MAIL,
                recipients=[email_address, ADMIN_MAIL])
        msg.body = render_template("alert_email.txt", 
            event=event)
        msg.html = render_template("alert_email.html", 
            event=event)
        mail.send(msg)

# send disapprove email
@async
def send_disapprove_mail(event, email_address):
    with app.test_request_context():
        msg = Message(
                'Your Booking is not approved',
                sender=SERVICE_MAIL,
                recipients=[email_address])
        msg.body = render_template("disapprove_email.txt", 
            event=event)
        msg.html = render_template("disapprove_email.html", 
            event=event)
        mail.send(msg)


# FRONT-END METHODS
@async
def to_approve(eid):
    eid = str(eid).strip()
    service = authorize()
    updated_event = service.events().move(calendarId=PENDING_CAL_ID, eventId=eid, destination=APPROVED_CAL_ID).execute()
    update_spreadsheet(updated_event['id'], eid, 'Approved')
    event_json = created_event_to_json(updated_event)
    email_address = updated_event['attendees'][0]['email']
    send_approve_mail(event_json, email_address)

@async
def to_disapprove(eid):
    eid = str(eid).strip()
    service = authorize()
    deleted_event = service.events().get(calendarId=PENDING_CAL_ID, eventId=eid).execute()
    update_spreadsheet(eid, eid, 'Disapproved')
    event_json = created_event_to_json(deleted_event)
    email_address = deleted_event['attendees'][0]['email']
    service.events().delete(calendarId=PENDING_CAL_ID, eventId=eid).execute()
    send_disapprove_mail(event_json, email_address)

def create_event_and_log(event, apptRoom, apptContact, apptPeople):
    service = authorize()
    created_event = service.events().insert(calendarId=PENDING_CAL_ID, body=event).execute()
    log = {
        'id': str(created_event['id']),
        'timestamp': str(datetime.datetime.now()),
        'name': str(session['name']),
        'matric': str(session['openid'])[-8:],
        'room': str(apptRoom),
        'purpose': str(created_event['description']),
        'starttime': str(created_event['start']['dateTime']),
        'endtime': str(created_event['end']['dateTime']),
        'email': str(created_event['attendees'][0]['email']),
        'phone': str(apptContact),
        'people': str(apptPeople),
        'status': 'Pending',
        'approved_time': 'N/A'
    }
    send_alert_mail(log, GROUP_MAIL)
    to_spreadsheet(log)
    return created_event

def created_event_to_json(event):
    eid = event['id']
    newApptName = event['summary']
    newApptStart = event['start']['dateTime']
    newApptEnd = event['end']['dateTime']
    newApptPurpose = event['description']

    start_formatted = parser.parse(newApptStart).strftime("%d/%m/%Y at %H:%M")
    end_formatted = parser.parse(newApptEnd).strftime("%d/%m/%Y at %H:%M")
    start_time = parser.parse(newApptStart).strftime("%H:%M")
    end_time = parser.parse(newApptEnd).strftime("%H:%M")
    date = parser.parse(newApptEnd).strftime("%d/%m")


    json = {
        'id': eid.strip(),
        'name': newApptName,
        'date': date,
        'start': start_formatted,
        'start_time': start_time,
        'end': end_formatted,
        'end_time':end_time,
        'purpose': newApptPurpose
    }

    return json

def get_existing_events(existing_start_rfc3339, existing_end_rfc3339):
    service = authorize()
    existing_event_list = service.events().list(calendarId=PENDING_CAL_ID, timeMin=existing_start_rfc3339, timeMax=existing_end_rfc3339).execute()['items']
    existing_event_list.extend(service.events().list(calendarId=APPROVED_CAL_ID, timeMin=existing_start_rfc3339, timeMax=existing_end_rfc3339).execute()['items'])
    return existing_event_list

#  ##     ## #### ######## ##      ## 
#  ##     ##  ##  ##       ##  ##  ## 
#  ##     ##  ##  ##       ##  ##  ## 
#  ##     ##  ##  ######   ##  ##  ## 
#   ##   ##   ##  ##       ##  ##  ## 
#    ## ##    ##  ##       ##  ##  ## 
#     ###    #### ########  ###  ###  

# Error
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

@app.route('/favicon.ico')
def favicon():
    return send_from_directory("/static", "favicon.ico")

# Login
@app.route('/', methods=['GET', 'POST'])
@oid.loginhandler
def login():
    if 'openid' in session:
        return redirect(url_for('search'))
    if request.method == 'POST':
        matric = request.form.get('openid')
        session['matric'] = matric
        session['is_admin'] = validate_admin_from_spreadsheet(session['matric'])
        if not validate_permit_from_spreadsheet(matric):
            return render_template('access_denied.html')
        openid = "http://openid.nus.edu.sg/" + matric
        if openid:
            return oid.try_login(openid, ask_for=['email', 'fullname'])
    return render_template('login.html', next=oid.get_next_url(),
                           error=oid.fetch_error())

@oid.after_login
def create_or_login(resp):
    session['openid'] = resp.identity_url
    session['name'] = resp.fullname
    session['email'] = resp.email
    print resp.fullname
    print session['openid']
    return redirect(url_for('search', next=oid.get_next_url()))

@app.route('/logout')
def logout():
    session.clear()
    flash(u'You were signed out')
    return redirect(url_for('login'))

@app.route("/search", methods=['GET', 'POST'])
def search():
    if 'openid' not in session:
        return redirect(url_for('login'))
    else: 
        calendar_list = [get_pending_cal()]
        return render_template('search.html', calendar_list=calendar_list, name=session['name'])

@app.route('/approve', methods=['GET', 'POST'])
def approve():
    if 'matric' not in session:
        return redirect(url_for('search'))
    elif not validate_admin_from_spreadsheet(session['matric']):
        return render_template('access_denied.html')
    else:
        event_list = get_pending_events()
        return render_template('approve.html', event_list = event_list)

@app.route("/search_events", methods=['POST', 'GET'])
def search_events():
    if 'openid' not in session:
        return redirect(url_for('login'))
    else: 
        startdate = request.form['apptStartDate']
        starttime = request.form['apptStartTime']
        enddate = request.form['apptStartDate']
        endtime = request.form['apptEndTime']
        calendarIdTimezone = request.form['calendarlist'].split()
        calendarid = calendarIdTimezone[0]
        calendarTimezone = calendarIdTimezone[1]
        # format start and end times
        start_dt = datetime.datetime.strptime(starttime, '%H:%M').time()
        end_dt = datetime.datetime.strptime(endtime, '%H:%M').time()
        start_formatted = start_dt.strftime("%I:%M%p")
        end_formatted = end_dt.strftime("%I:%M%p")
        # get list of free dates (datetime objects)
        free_dates = generate_date_list(startdate, enddate, starttime, endtime, calendarid)
        free_dates_string = []
        # convert free dates into a more reader friendly string
        for date in free_dates:
            free_dates_string.append(date.strftime("%m/%d/%Y"))
        # send list of free dates to render on suggestions page
        print free_dates_string
        return render_template("suggestions.html", free_dates=free_dates_string, starttime=start_formatted, endtime=end_formatted, calendarid=calendarid, timezone=calendarTimezone)

@app.route("/approve_booking", methods=['POST', 'GET'])
def approve_booking():
    if 'matric' not in session:
        return redirect(url_for('search'))
    elif not validate_admin_from_spreadsheet(session['matric']):
        return render_template('access_denied.html')
    else:
        eventId = request.form.getlist('eventlist')
        print eventId
        for eid in eventId:
            to_approve(eid)
        return redirect(url_for('approve'))

@app.route("/disapprove_booking/<eid>", methods=['POST', 'GET'])
def disapprove_booking(eid):
    if 'matric' not in session:
        return redirect(url_for('search'))
    elif not validate_admin_from_spreadsheet(session['matric']):
        return render_template('access_denied.html')
    else:
        if eid:
          to_disapprove(eid)
        return redirect(url_for('approve'))

@app.route("/schedule_event", methods=['POST', 'GET'])
def schedule_event():
    if 'openid' not in session:
        return redirect(url_for('login'))
    else: 
        #authorization
        service = authorize()

        # grab user inputs from the schedule_event form
        apptPeople = request.form['apptPeople']
        apptRoom = request.form['apptRoom']
        apptContact = request.form['apptContact']
        apptPurpose = request.form['apptPurpose']
        apptCalendarId = request.form['apptCalendarId']
        # from apptOptions, grab the start/end date and time user has chosen
        # apptOptions returns in format: 05/05/13, 12:00, 13:00
        # first, turn it into a list
        dt = request.form['apptOptions']
        rfc3339 = get_start_end_rfc3339(dt)
        # put all the data needed with the post request into a dictionary

        name = session['name'], " (Pending)"
        email = session['email']

        event = {
            'summary': name,
            'description': apptPurpose,
            'start': {
                'dateTime': rfc3339['start'],
                'timeZone': rfc3339['timezone']
            },
            'end': {
                'dateTime': rfc3339['end'],
                'timeZone': rfc3339['timezone']
            },
            'colorId': '3',
            'attendees':[
                { 'email' : email,

                'displayName': name }
            ]
        }
        
        existing_event_list = get_existing_events(rfc3339['startdt'], rfc3339['enddt'])

        if len(existing_event_list) == 0:
            created_event = create_event_and_log(event, apptRoom, apptContact, apptPeople)
        else:
            created_event = None
            return render_template("success.html", event=created_event)
        json = created_event_to_json(created_event)

        return render_template("success.html", event=created_event, apptName=json['name'], apptStart=json['start'], apptEnd=json['end'], apptPurpose=json['purpose'])

if __name__ == "__main__":
  app.run(debug=True)