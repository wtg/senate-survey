from functools import wraps
from flask import Flask, session, redirect, url_for, request, jsonify, render_template, abort, send_file, request, Response
from flask_cas import CAS, login_required, login, logout

import csv
import datetime
import hashlib
import io
import json
import os
import uuid

import models


def get_pepper():
    try:
        return os.environ['SURVEY_PEPPER']
    except:
        return None


def json_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    if isinstance(obj, uuid.UUID):
        return str(obj)
    raise TypeError('{} is not JSON serializable'.format(type(obj)))


app = Flask(__name__)
cas = CAS(app)
app.config['CAS_SERVER'] = 'https://cas-auth.rpi.edu/cas/'
app.config['CAS_AFTER_LOGIN'] = 'form'
SURVEY_VERSION = 3

CC_SURVEY_ADMINS = set(os.getenv('SURVEY_ADMINS', '').split(','))
CLOSED = bool(os.getenv('SURVEY_CLOSED', False))

SURVEY = [
    [
        {
            "id": "demographic1",
            "question": "Which class are you a part of?",
            "type": "select",
            "options": [
                "Freshman",
                "Sophomore",
                "Junior",
                "Senior",
                "Co-terminal",
                "Masters",
                "Doctorate"
            ],
            "required": True
        },
        {
            "id": "demographic2",
            "question": "Are you a member of a Greek-affiliated organization",
            "type": "radio",
            "options": [
                "Yes, Panhellenic Council",
                "Yes, Interfraternity Council",
                "No"
            ],
            "inline": False,
            "required": True
        },
        {
            "id": "demographic3",
            "question": "As of the Fall 2016 semester, where do you currently live?",
            "type": "radio",
            "options": [
                "On-campus residence hall or apartment",
                "Greek housing",
                "Off-campus"
            ],
            "inline": False,
            "required": True
        },
        {
            "id": "reslife1",
            "question": "In which residence hall do you live?",
            "type": "select",
            "options": [
                "BARH",
                "Barton Hall",
                "Blitman Residence Commons",
                "Bray Hall",
                "Bryckwyck",
                "Cary Hall",
                "City Station West",
                "Colonie Apartments",
                "Crockett Hall",
                "Davison Hall",
                "E-Complex",
                "Hall Hall",
                "Nason Hall",
                "North Hall",
                "Nugent Hall",
                "Polytechnic Residence Commons",
                "Quadrangle",
                "RAHP A",
                "RAHP B",
                "Sharp Hall",
                "Stacwyck Apartments",
                "Warren Hall"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife2",
            "question": "Which of the following reasons motivated you to live on-campus?",
            "type": "checkbox",
            "options": [
                "Sense of community",
                "Location",
                "Safety",
                "Cleanliness",
                "Cost",
                "Utilities",
                "Privacy",
                "Space",
                "Convenience (FIXX, cleaning staff, study rooms, etc.)",
                "Required to"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife3",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the toilets in your residence halls?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife4",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the sinks in your residence halls?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife5",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the bathroom countertops in your residence halls?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife6",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the showers in your residence halls?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife7",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the dispensers in your residence halls?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife8",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with your residence hall's printer(s)?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife9",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with your residence hall's study rooms?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife10",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with your residence hall's kitchen?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife11",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with your residence hall's communal furniture?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife12",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with you residence hall’s timeliness of FIXX responses (how long it takes for your issue to be resolved)?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife13",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with you residence hall’s Wi-Fi connection?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife14",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with you residence hall’s bedroom furniture?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife15",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with you residence hall’s air conditioning (if applicable)?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife16",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with you residence hall’s heating?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife17",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with your hall's programs and activities?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife18",
            "question": "If you chose 3 or less for any of the scaled questions about the state of your on-campus housing, please elaborate here.",
            "type": "text",
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment"
        },
        {
            "id": "reslife19",
            "question": "Have you ever felt unsafe near the entrance to your building (due to stalkers, loitering, etc)?",
            "type": "radio",
            "options": ["Yes", "No"],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife20",
            "question": "Would you feel more safe to have multiple entrances to your building that are not alarmed?",
            "type": "radio",
            "options": ["Yes", "No"],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife21",
            "question": "Have you been educated on what to do in emergency situations in your building (such as an active shooter, weather disaster, fire, etc.)?",
            "type": "radio",
            "options": ["Yes", "No"],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife22",
            "question": "What Department of Public Safety services have you used (such as rides when you feel unsafe, blue light system, etc.)?",
            "type": "text",
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment"
        },
        {
            "id": "reslife23",
            "question": "Which of the following statements best match your beliefs with respect to access to other residence halls?",
            "type": "select",
            "options": [
                "Residents should only have access to their own residence hall",
                "On-campus residents should have access to neighboring residence halls, but only during daylight hours",
                "On-campus residents should have access to neighboring residence halls",
                "On-campus residents should have access to all residence halls, but only during daylight hours",
                "On-campus residents should have access to all residence halls"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife24",
            "question": "On a scale from 1-10, ten being the highest, how important is the presence of food at a program to your willingness to attend?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife25",
            "question": "Are you aware of, or familiar with, the Guest Policy?",
            "type": "radio",
            "options": ["Yes", "No"],
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment",
            "required": True
        },
        {
            "id": "reslife26",
            "question": "If you have any other comments about the state of your on-campus housing, please share them here.",
            "type": "text",
            "show_if_id": "demographic3",
            "show_if_value": "On-campus residence hall or apartment"
        },
        {
            "id": "greekHousing1",
            "question": "As of the Fall 2016 semester, how long have you lived in Greek housing?",
            "type": "radio",
            "options": [
                "1-2 semesters",
                "3-4 semesters",
                "5 or more semesters"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing2",
            "question": "How many semesters did you live on-campus before moving into your Greek house?",
            "type": "radio",
            "options": [
                "Did not live on-campus",
                "1-2 semesters",
                "3-4 semesters",
                "5 or more semesters"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing3",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the cost of living in your Greek house in comparison to other options?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing4",
            "question": "If you were to have participated in the Summer Arch program, or if you plan to, would you have preferred to live in your Greek house for the summer semester?",
            "type": "radio",
            "options": ["Yes", "No"],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing5",
            "question": "What was your primary motivation for living in a Greek House?",
            "type": "radio",
            "options": [
                "Sophomore who didn’t want to live in on-campus",
                "Cost",
                "It’s required by my chapter",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing5other",
            "question": "What was your primary motivation for living in a Greek House?",
            "type": "text",
            "show_if_id": "greekHousing5",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "greekHousing6",
            "question": "Are you planning on continuing to live in your Greek House for the 2017-2018 Academic Year?",
            "type": "radio",
            "options": [
                "Yes",
                "No, graduating",
                "No, not planning to"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing7",
            "question": "Do you have an RPI shuttle stop that stops near your house?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing8",
            "question": "Do you use the shuttle stop near your house to commute between your house and campus?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "greekHousing7",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "greekHousing9",
            "question": "If there was a shuttle stop near your house, would you use it to commute between your house and campus?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "greekHousing7",
            "show_if_value": "No",
            "required": True
        },
        {
            "id": "greekHousing10",
            "question": "Do you feel safe in the area where your Greek house is?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing11",
            "question": "Have you ever had an incident occur off-campus in which you felt unsafe?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing12",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the presence of Public Safety and/or Troy Police in your neighborhood?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing13",
            "question": "Do you have a Blue Light Station near your Greek house?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing14",
            "question": "If you do not have a Blue Light Station near your Greek house, would you feel more safe if there was one?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "greekHousing13",
            "show_if_value": "No"
        },
        {
            "id": "greekHousing15",
            "question": "In case of an incident, who would you be most comfortable calling?",
            "type": "radio",
            "options": [
                "Department of Public Safety",
                "Troy Police Department",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing15other",
            "question": "In case of an incident, who would you be most comfortable calling?",
            "type": "text",
            "show_if_id": "greekHousing15",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "greekHousing16",
            "question": "Approximately how far away is your Greek House from campus?",
            "type": "radio",
            "options": [
                "0 - 0.5 miles",
                "0.5 - 2 miles",
                "2 - 5 miles",
                "5+ miles"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing17",
            "question": "How do you primarily commute to campus?",
            "type": "radio",
            "options": [
                "Walking",
                "Driving",
                "Biking, skateboarding, etc.",
                "Shuttle",
                "Public Transportation",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing17other",
            "question": "How do you primarily commute to campus?",
            "type": "text",
            "show_if_id": "greekHousing17",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "greekHousing18",
            "question": "Do you have a parking pass?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "required": True
        },
        {
            "id": "greekHousing19",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the availability of parking passes?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "greekHousing18",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "greekHousing20",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the availability of parking spaces on campus?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "greekHousing18",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "greekHousing21",
            "question": "What was your motivation to live on campus when you did?",
            "type": "checkbox",
            "options": [
                "Sense of community",
                "Location",
                "Safety",
                "Cleanliness",
                "Cost",
                "Utilities",
                "Privacy",
                "Space",
                "Convenience (FIXX, cleaning staff, study rooms, etc.)",
                "Required to",
                "Did not live on campus"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing22",
            "question": "Approximately how long does it take you to get to class?",
            "type": "radio",
            "options": [
                "Less than 5 minutes",
                "5-10 minutes",
                "10-15 minutes",
                "15-20 minutes",
                "20+ minutes"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing",
            "inline": False,
            "required": True
        },
        {
            "id": "greekHousing23",
            "question": "If you have any other comments about your experiences with Greek Housing, please share them here.",
            "type": "text",
            "show_if_id": "demographic3",
            "show_if_value": "Greek housing"
        },
        {
            "id": "offcampus1",
            "question": "How did you find out about your off-campus housing?",
            "type": "radio",
            "options": [
                "Jump Off Campus",
                "Friend",
                "Craigslist",
                "Zillow",
                "Facebook groups associated with RPI and/or Troy (Free & For Sale, etc)",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "inline": False,
            "required": True
        },
        {
            "id": "offcampus1other",
            "question": "How did you find out about your off-campus housing?",
            "type": "text",
            "show_if_id": "offcampus1",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "offcampus2",
            "question": "Approximately how far away do you live from campus?",
            "type": "radio",
            "options": [
                "0 - 0.5 miles",
                "0.5 - 2 miles",
                "2 - 5 miles",
                "5+ miles"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus3",
            "question": "How do you primarily commute to campus?",
            "type": "radio",
            "options": [
                "Walking",
                "Driving",
                "Biking, skateboarding, etc.",
                "Shuttle",
                "Public Transportation",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "inline": False,
            "required": True
        },
        {
            "id": "offcampus3other",
            "question": "How do you primarily commute to campus?",
            "type": "text",
            "show_if_id": "offcampus3",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "offcampus4",
            "question": "Approximately how long does it take you to get to class?",
            "type": "radio",
            "options": [
                "Less than 5 minutes",
                "5-10 minutes",
                "10-15 minutes",
                "15-20 minutes",
                "20+ minutes"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "inline": False,
            "required": True
        },
        {
            "id": "offcampus5",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the overall quality of your off-campus housing and amenities?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus6",
            "question": "Do you have a parking pass?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus7",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the availability of parking passes?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "offcampus6",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "offcampus8",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the availability of parking spaces on campus?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10, "N/A"
            ],
            "show_if_id": "offcampus6",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "offcampus9",
            "question": "Do you feel safe around the area where you live?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus10",
            "question": "Have you ever had an incident occur in which you felt unsafe?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus11",
            "question": "On a scale from 1-10, ten being the highest, how satisfied are you with the presence of Public Safety and/or Troy Police in your neighborhood?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus12",
            "question": "Do have a Blue Light Station near where you live?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus13",
            "question": "If you do not have a Blue Light Station near where you live, would you feel more safe if there was one?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "offcampus12",
            "show_if_value": "No",
            "required": True
        },
        {
            "id": "offcampus14",
            "question": "In case of an incident, who would you be most comfortable calling?",
            "type": "radio",
            "options": [
                "Department of Public Safety",
                "Troy Police Department",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "inline": False,
            "required": True
        },
        {
            "id": "offcampus14other",
            "question": "In case of an incident, who would you be most comfortable calling?",
            "type": "text",
            "show_if_id": "offcampus14",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "offcampus15",
            "question": "What was your motivation to live off campus?",
            "type": "checkbox",
            "options": [
                "Cost",
                "Less regulations",
                "Privacy",
                "Ability to not be on a meal plan",
                "Location",
                "Cleanliness",
                "More Freedom",
                "Better Utilities (Internet, etc)",
                "Living at home / with family",
                "Space",
                "Other (please specify below)"
            ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "inline": False,
            "required": True
        },
        {
            "id": "offcampus15other",
            "question": "What was your motivation to live off campus?",
            "type": "text",
            "show_if_id": "offcampus15",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "offcampus16",
            "question": "Though living off-campus, do you still feel connected to the campus community?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus17",
            "question": "Did you live on-campus before moving off campus?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus18",
            "question": "How many semesters did you live on-campus before moving off campus?",
            "type": "radio",
            "options": [
                "1-2 semesters",
                "3-4 semesters",
                "5 or more semesters"
            ],
            "show_if_id": "offcampus17",
            "show_if_value": "Yes",
            "required": True
        },
        {
            "id": "offcampus19",
            "question": "How many semesters did you live on-campus before moving off campus?",
            "type": "radio",
            "options": [
                "Sense of community",
                "Location",
                "Safety",
                "Cleanliness",
                "Cost",
                "Utilities",
                "Privacy",
                "Space",
                "Convenience (FIXX, cleaning staff, study rooms, etc.)",
                "Required to"
            ],
            "show_if_id": "offcampus17",
            "show_if_value": "Off-campus",
            "required": True
        },
        {
            "id": "offcampus20",
            "question": "If you have any other comments about your experiences with off-campus living, please share them here.",
            "type": "text",
            "show_if_id": "demographic3",
            "show_if_value": "Off-campus"
        }
    ],
    [
        {
            "id": "summerPrograms1",
            "question": "Have you lived in the Troy area over the summer before?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "summerPrograms2",
            "question": "On a scale from 1-10, ten being the highest, how satisfied were you with availability of options for activities on campus and in the local area?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ],
            "show_if_id": "summerPrograms1",
            "show_if_value": "Yes"
        },
        {
            "id": "summerPrograms3",
            "question": "If any, what suggestions do you have for activities for students living near campus in the summer?",
            "type": "text"
        },
        {
            "id": "rights1",
            "question": "On a scale from 1-10, ten being the highest, how familiar are you with the Rensselaer Handbook of Rights and Responsibilities (commonly referred to as the Student Handbook)?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "rights2",
            "question": "On a scale from 1-10, ten being the highest, how familiar are you with the Good Samaritan Policy?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "rights3",
            "question": "Do you have any concerns or issues with any student-related policies?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "rights4",
            "question": "If yes, what concerns or issues do you have?",
            "type": "text",
            "show_if_id": "rights3",
            "show_if_value": "Yes"
        },
        {
            "id": "rights5",
            "question": "If you have any other comments about student rights and/or policies, please share them here.",
            "type": "text"
        },
        {
            "id": "pharmacy1",
            "question": "Do you regularly take prescription medication?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "pharmacy2",
            "question": "How often do you pick up prescriptions?",
            "type": "radio",
            "options": [
                "Weekly",
                "Monthly",
                "Every 3 months",
                "Once per year"
            ],
            "show_if_id": "pharmacy1",
            "show_if_value": "Yes",
            "inline": False
        },
        {
            "id": "pharmacy3",
            "question": "Would you be interested in having prescriptions mailed to you on campus instead of picking them up at a pharmacy?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "pharmacy1",
            "show_if_value": "Yes"
        },
        {
            "id": "pharmacy4",
            "question": "Do you already have prescriptions mailed to you?",
            "type": "radio",
            "options": [ "Yes", "No" ],
            "show_if_id": "pharmacy1",
            "show_if_value": "Yes"
        },
        {
            "id": "pharmacy5",
            "question": "What company do you use to have prescriptions mailed to you?",
            "type": "text",
            "show_if_id": "pharmacy4",
            "show_if_value": "Yes"
        },
        {
            "id": "pharmacy6",
            "question": "How often do you need urgent, short-term prescriptions filled (like antibiotics)?",
            "type": "radio",
            "options": [
                "Very Often",
                "Somewhat Often",
                "Rarely",
                "Almost Never"
            ],
            "inline": False
        },
        {
            "id": "pharmacy7",
            "question": "Would it be more convenient for you to pick up an urgent prescription at an on-campus pharmacy in the case that you needed one?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "pharmacy8",
            "question": "Would you support the addition of a pharmacy to campus?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "pharmacy9",
            "question": "If there was a pharmacy on campus, would you use the pharmacy to fill your prescription medicine?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "pharmacy10",
            "question": "If there was a pharmacy on campus, would you use the pharmacy to obtain any needed over-the-counter medications?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "pharmacy11",
            "question": "If you have any other comments about prescription medication or pharmacies, please share them here.",
            "type": "text"
        },
        {
            "id": "study1",
            "question": "What locations on campus have you used to study?",
            "type": "text"
        },
        {
            "id": "study2",
            "question": "Which of the following issues have you found to be most common with study spaces?",
            "type": "radio",
            "options": [
                "Too crowded",
                "Too noisy",
                "I did not know about this location",
                "Too far away from where I live"
            ],
            "inline": False
        },
        {
            "id": "study3",
            "question": "On a scale from 1-10, ten being the highest, how regularly do you use the '87 Gym?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "study4",
            "question": "If the spaces were renovated, equipped, and prepared, would you consider using the ‘87 Gym for meetings for clubs and study rooms?",
            "type": "radio",
            "options": [ "Yes", "No" ]
        },
        {
            "id": "study5",
            "question": "If you have any other comments about on-campus study spaces, please share them here.",
            "type": "text"
        },
        {
            "id": "foods1",
            "question": "On a scale from 1-10, how satisfied are you with the level of diversity of foods offered on campus?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "foods2",
            "question": "On a scale from 1-10, how satisfied are you with the level of diversity of foods offered specifically in the Union?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "foods3",
            "question": "What types of cuisine would you like to see that you don’t currently see on campus?",
            "type": "text"
        },
        {
            "id": "foods4",
            "question": "What types of cuisine would you like to see that you don’t currently see on campus?",
            "type": "checkbox",
            "options": [
                "Mexican: Rice Bowls, burritos, Quesadillas, Enchiladas",
                "Western Mediterranean: Pastas, Greek Spinach Strudel, Paella",
                "Eastern Mediterranean: Lentil Stew, Hummus Wrap, Pilaf, Chickpea Couscous Burger",
                "Asia: Rice Noodles, Fried Noodles, Stir fry",
                "North Africa: Vegetable Stew, Moroccan Couscous, Chickpea Soup, Pita Bread",
                "Central & South Africa: African vegetable curry,Ethiopian Vegetable Stew, Vegan Potato, Peanut & Vegetable Curry",
                "Other (please specify below)"
            ],
            "inline": False
        },
        {
            "id": "foods4other",
            "question": "",
            "type": "text",
            "show_if_id": "foods4",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "foods5",
            "question": "How frequently do you patronize restaurants in downtown Troy?",
            "type": "radio",
            "options": [
                "Never",
                "A few times per year",
                "Once per month",
                "Once per week",
                "Multiple times per week"
            ],
            "inline": False
        },
        {
            "id": "empac1",
            "question": "How often do you attend shows at EMPAC?",
            "type": "radio",
            "options": [
                "Never",
                "One to two times a semester",
                "Three to four times a semester",
                "More than five"
            ],
            "inline": False
        },
        {
            "id": "empac2",
            "question": "What kind of performances have you attended?",
            "type": "checkbox",
            "options": [
                "Performance",
                "Talk",
                "Music/Sound",
                "Film/Video",
                "Town Hall Meetings",
                "Union Speaker Forum",
                "Student Club Performance",
                "Dance",
                "School of Architecture Lectures",
                "MFA Art Student Performances"
            ],
            "inline": False
        },
        {
            "id": "empac3",
            "question": "What motivated you to go to the performance?",
            "type": "checkbox",
            "options": [
                "Mandatory",
                "Personal Interest",
                "Went with a friend",
                "Other (please specify below)"
            ],
            "inline": False
        },
        {
            "id": "empac3other",
            "question": "",
            "type": "text",
            "show_if_id": "empac3",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "empac4",
            "question": "How did you hear about the performances?",
            "type": "checkbox",
            "options": [
                "Morning Mail",
                "Concerto",
                "Email",
                "Friends",
                "Posters",
                "EMPAC Catalog",
                "Professor's Recommendation"
            ],
            "inline": False
        },
        {
            "id": "empac5",
            "question": "Are you interested in the types of performances that EMPAC currently offers?",
            "type": "radio",
            "options": ["Yes", "No"]
        },
        {
            "id": "empac6",
            "question": "Which of the following shows would you be willing to see if offered at EMPAC?",
            "type": "checkbox",
            "options": [
                "Movie Night",
                "Talks from Industry Leaders/Researchers",
                "TEDx (unaffiliated TED Talks)",
                "Club Affiliated Events (RPI Players, Orchestra, etc.)",
                "GM Week Activities",
                "Video Game Demos",
                "Other (please specify below)"
            ]
        },
        {
            "id": "empac6other",
            "question": "",
            "type": "text",
            "show_if_id": "empac6",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "empac7",
            "question": "Have you ever eaten in EMPAC?",
            "type": "radio",
            "options": [
                "Yes, at Evelyn's",
                "Yes, at Terra Cafe",
                "Yes, at both",
                "No"
            ],
            "inline": False
        },
        {
            "id": "empac8",
            "question": "Have you heard of EMPAC+?",
            "type": "radio",
            "options": [
                "Yes, and I'm a member",
                "Yes, but I'm not a member",
                "No"
            ],
            "inline": False
        }
    ],
    [
        {
            "id": "aac1",
            "question": "Have you ever seen someone cheating on a test/quiz?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True
        },
        {
            "id": "aac2",
            "question": "How were they cheating?",
            "type": "checkbox",
            "options": [
                "Laptop",
                "Cell phone",
                "Notes or crib sheets",
                "Other (please specify below)"
            ],
            "show_if_id": "aac1",
            "show_if_value": "Yes"
        },
        {
            "id": "aac2other",
            "question": "",
            "type": "text",
            "show_if_id": "aac2",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "aac3",
            "question": "Did your TA or professor notice the incident?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True,
            "show_if_id": "aac1",
            "show_if_value": "Yes"
        },
        {
            "id": "aac4",
            "question": "Did they do anything about it on the scene?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True,
            "show_if_id": "aac3",
            "show_if_value": "Yes"
        },
        {
            "id": "aac5",
            "question": "In general, do your TAs walk around during exams and check for cheating?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True
        },
        {
            "id": "aac6",
            "question": "Have you ever reported someone for cheating?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True
        },
        {
            "id": "aac7",
            "question": "Do you feel that those who are not cheating are being taken advantage of?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True
        },
        {
            "id": "aac8",
            "question": "Do you feel RPI degrees are blemished by the amount of cheating within classes?",
            "type": "radio",
            "options": ["Yes", "No"],
            "inline": True
        },
        {
            "id": "aac9",
            "question": "How bad of a problem do you think cheating is at RPI?",
            "type": "radio",
            "options": [
                1, 2, 3, 4, 5, 6, 7, 8, 9, 10
            ]
        },
        {
            "id": "aac10",
            "question": "Would you support removing an academic holiday (Columbus Day) so that there would be no classes on the date of the Career Fair?",
            "type": "radio",
            "options": ["Yes", "No"]
        }
    ],
    [
        {
            "id": "comm1",
            "question": "How do you hear about Student Government Projects and Events?",
            "type": "checkbox",
            "options": [
                "Facebook RPI: Get Informed Page",
                "Student Government Twitter",
                "RPI Reddit",
                "Posters",
                "Tabling Info Sessions on Campus",
                "The Polytechnic (Newspaper)",
                "Open Student Government Meetings",
                "Word of Mouth",
                "Other (please specify below)"
            ]
        },
        {
            "id": "comm1other",
            "question": "",
            "type": "text",
            "show_if_id": "comm1",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "comm2",
            "question": "What is the best way to be notified about Student Government Projects and Events?",
            "type": "radio",
            "options": [
                "Facebook RPI: Get Informed Page",
                "Student Government Twitter",
                "RPI Reddit",
                "Posters",
                "Tabling Info Sessions on Campus",
                "The Polytechnic (Newspaper)",
                "Open Student Government Meetings",
                "Word of Mouth",
                "Other (please specify below)"
            ],
            "inline": False
        },
        {
            "id": "comm2other",
            "question": "",
            "type": "text",
            "show_if_id": "comm2",
            "show_if_value": "Other (please specify below)"
        },
        {
            "id": "comm3",
            "question": "How many Student Government projects and events have you heard of in the last year?",
            "type": "radio",
            "options": [
                0, 1, 2, 3, 4, "5+"
            ]
        },
        {
            "id": "comm3other",
            "question": "What projects have you heard of?",
            "type": "text",
            "show_if_id": "comm3",
            "show_if_value_not": "0"
        },
        {
            "id": "comm4",
            "question": "Would you like to see monthly write-ups about Student Government projects and events?",
            "type": "radio",
            "options": ["Yes", "No"]
        },
        {
            "id": "comm5",
            "question": "In what way could your Student Officials be in better contact with you?",
            "type": "text"
        }
    ],
    [
        {
            "id": "other1",
            "question": "If you have any other feedback, please share it here.",
            "type": "text"
        },
        {
            "id": "raffle1",
            "question": "If you would like to be entered in a raffle for a gift card to the Collegiate Store, please enter your email address below.",
            "type": "email"
        }
    ]
]


def hash_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session['hash'] = hash()
        return f(*args, **kwargs)
    return decorated_function


def check_pepper(f):
    @wraps(f)
    def func(*args, **kwargs):
        if get_pepper() is None:
            return not_configured()
        return f(*args, **kwargs)
    return func


def hash():
    """Generate a hash of the user's RCS ID.

    Appends a pepper from the environment. This makes it harder to brute-force
    RCS IDs to reverse these hashes, assuming that the pepper is kept secret.
    The survey version is also included in the hash so that a new version of
    the survey can be taken by someone who has taken a previous version.
    """
    pepper = get_pepper()
    if pepper is None:
        return not_configured()
    to_hash = cas.username + pepper + str(SURVEY_VERSION)
    return hashlib.md5(to_hash.encode()).hexdigest()


def get_question_for_key(key):
    orig_key = key # keep original key to append to question before return

    # strip list notation from multiple choice questions to get original q
    if key.endswith('[]'):
        key = key[:-2]

    # strip other to get original q
    if key.endswith('other'):
        key = key[:-5]
    for question in [item for sublist in SURVEY for item in sublist]:
        if question['id'] == key:
            return question['question'] + ' ({})'.format(orig_key)
            if other:
                q += ' (other)'
            return q
    return key


@app.before_request
def check_closed():
    if CLOSED and request.path.startswith('/form'):
        # Redirect all /form paths to / if survey is closed
        return redirect('/')


@app.route('/form', methods=['GET', 'POST'])
@check_pepper
@login_required
@hash_request
def form():
    with models.db.atomic():
        # Check if a submission from this user has already been received.
        # This and inserting new submissions should be done atomically to avoid
        # race conditions with multiple submissions from the same user at the
        # same time.
        if len((models.UserHash
                .select()
                .where(models.UserHash.hash == session['hash']))) != 0:
            return render_template('message.html',
                                   message="You've already responded to this survey.",
                                   title='Already responded')

        # Insert into database if UserHash is new
        if request.method == 'POST':

            # No previous submission; record this one.
            models.UserHash().create(hash=session['hash'])

            # Dump form to JSON
            form = {}
            for key in request.form.keys():
                lst = request.form.getlist(key)
                if key.endswith('[]'):
                    form[key] = lst
                else:
                    assert(len(lst) == 1)
                    val = lst[0]
                    if val == '':
                        continue
                    form[key] = val
            form_json = json.dumps(form)

            models.Submission().create(form=form_json, version=SURVEY_VERSION)

            return render_template('message.html', message="""Your submission has
                been recorded anonymously. Thank you for your participation in the survey
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            return render_template('form.html',
                                   title='Take survey')


@app.route('/form/<auth_key>', methods=['GET', 'POST'])
@check_pepper
def form_auth_key(auth_key):
    with models.db.atomic():
        # Check if this is a valid survey authorization key.
        # This and inserting new submissions should be done atomically to avoid
        # race conditions with multiple submissions with the same key at the
        # same time.
        key_models = (models.AuthorizationKey
                      .select()
                      .where(models.AuthorizationKey.key == auth_key))
        if len(key_models) != 1:
            return render_template('message.html',
                                   message="Invalid authorization key.",
                                   title='Not authorized')

        # Insert into database if UserHash is new
        if request.method == 'POST':

            # Delete this authorization key. We can assume len == 0 because of
            # the check a few lines above.
            key_models[0].delete_instance()

            # Dump form to JSON
            form_json = json.dumps(request.form)
            models.Submission().create(form=form_json, version=SURVEY_VERSION)

            return render_template('message.html', message="""Your submission has
                been recorded anonymously. Thank you for your participation in the survey
                and your contribution to improving the student experience at
                Rensselaer.""", title='Submission recorded')

        else:
            return render_template('form.html',
                                   title='Take survey')


@app.route('/export')
@login_required
def export():
    # see if this user is in CC_SURVEY_ADMINS
    if cas.username not in CC_SURVEY_ADMINS:
        abort(403)
    return render_template('export.html')


@app.route('/export.csv')
@login_required
def export_csv():
    def generate():
        # loop through all submissions and make a dict for each, then append to list
        submissions = models.Submission.select().order_by(models.Submission.time.desc())

        # build header. have to loop through everything because CSV
        header = ['id', 'time', 'version'] # CSV header containing all questions/keys
        for submission in submissions:
            # form is stored as JSON, so extract responses
            form_js = json.loads(submission.form)

            # if we only want responses to some questions, include only those
            for key, value in form_js.items():
                if question_prefix is None or key.startswith(question_prefix):
                    question = get_question_for_key(key)
                    if question not in header:
                        header.append(question)

        # output CSV
        line = io.StringIO()
        w = csv.DictWriter(line, header)
        w.writeheader()

        # loop through submissions again and stream output to client
        for submission in submissions:
            sub = {}
            sub['id'] = submission.id
            sub['time'] = submission.time
            sub['version'] = submission.version

            # form is stored as JSON, so extract responses
            form_js = json.loads(submission.form)

            # if we only want responses to some questions, include only those
            for key, value in form_js.items():
                if question_prefix is None or key.startswith(question_prefix):
                    question = get_question_for_key(key)
                    sub[question] = value

            w.writerow(sub)
            line.seek(0)
            yield line.read()
            line.truncate(0)


    # see if this user is in CC_SURVEY_ADMINS
    if cas.username not in CC_SURVEY_ADMINS:
        abort(403)

    question_prefix = request.args.get('question_prefix')
    # attachment filename
    if question_prefix is None:
        filename = 'senate-survey.csv'
    else:
        filename = 'senate-survey-{}.csv'.format(question_prefix)

    response = Response(generate(), mimetype='text/csv')
    response.headers['Content-Disposition'] = 'attachment; filename=' + filename
    return response


@app.route('/export.json')
@login_required
def export_json():
    # see if this user is in CC_SURVEY_ADMINS
    if cas.username not in CC_SURVEY_ADMINS:
        abort(403)

    # loop through all submissions and make a dict for each, then append to list
    submissions = models.Submission.select().order_by(models.Submission.time.desc())

    exp = []
    for submission in submissions:
        sub = {}
        sub['id'] = submission.id
        sub['time'] = submission.time
        sub['version'] = submission.version

        # form is stored as JSON, so extract responses
        form_js = json.loads(submission.form)

        # if we only want responses to some questions, include only those
        question_prefix = request.args.get('question_prefix')
        for key, value in form_js.items():
            if question_prefix is None or key.startswith(question_prefix):
                question = get_question_for_key(key)
                sub[question] = value

        exp.append(sub)

    # output JSON
    f = io.StringIO()
    json.dump({'responses': exp}, f, default=json_serializer)

    # there must be a better way to do this than StringIO -> str -> BytesIO
    return send_file(io.BytesIO(f.getvalue().encode('utf-8')),
                     mimetype='application/json')


@app.route('/')
def index():
    if CLOSED:
        # Return closed survey template if applicable
        return render_template('closed.html')
    return render_template('index.html')


def not_configured():
    return render_template('message.html',
                           title='Not configured',
                           message='Counseling Center Survey not configured.')


# set the secret key.  keep this really secret:
app.secret_key = os.environ['SECRET_KEY']
