#!/usr/bin/env python3

import json
import os
import requests
import sys
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import isfile, join, dirname

from dotenv import load_dotenv
from jinja2 import Template


dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path)

SEARCH_URL = os.environ['SEARCH_URL']
# TODO Implement paginated requests to increase max results over 30
MAX_RESULTS = 30

SMTP_USERNAME = os.environ['SMTP_USERNAME']
SMTP_PASSWORD = os.environ['SMTP_PASSWORD']
SMTP_HOSTNAME = os.environ['SMTP_HOSTNAME']
SMTP_PORT = os.environ['SMTP_PORT']

EMAIL_FROM = os.environ['EMAIL_FROM']
EMAIL_TO = os.environ['EMAIL_TO'].split(',')

def main():
    if len(sys.argv) == 1:
        search_name = os.environ['SEARCH_NAME']
        email_recipients = os.getenv('EMAIL_TO')
        search_parameters = os.environ['SEARCH_PARAMETERS']
    elif len(sys.argv) == 4:
        search_name = sys.argv[1]
        email_recipients = sys.argv[2]
        search_parameters = sys.argv[3]
    else:
        sys.exit(f'Usage: {sys.argv[0]} SEARCH_NAME EMAIL_RECIPIENTS SEARCH_PARAMETERS')
    
    html = get_new_ads_html(search_parameters, search_name)
    if html:
        with open(search_name_to_filename(search_name, 'html'), 'w') as new_ads_file:
            new_ads_file.write(html)
        if email_recipients:
            send_email(EMAIL_TO, search_name, html)


def get_new_ads_html(search_parameters, search_name):
    new_ads = get_new_ads(search_parameters, search_name)
    print(f'{len(new_ads)} new ads were found.')

    if len(new_ads) > 0:
        with open(join(dirname(__file__), 'email_template.html'), 'r') as email_template:
            template = Template(email_template.read())
        
        return template.render(search_name=search_name, new_ads=new_ads)


def get_new_ads(search_parameters, search_name):
    latest_ads = get_latest_ads(search_parameters, search_name)
    previous_ads = get_previous_ads(search_name)

    if len(previous_ads) == 0:
        new_ads = latest_ads
    else:
            new_ads = []
            for ad in latest_ads:
                if ad_is_new(ad, previous_ads):
                    new_ads.append(ad) 
                else:
                    break

    if len(new_ads) > 0:
        save_ads_to_file(new_ads, previous_ads, search_name)

    return new_ads


def get_latest_ads(search_parameters, search_name):
    response = requests.get(SEARCH_URL + search_parameters)

    if response.status_code != requests.codes.ok:
        sys.exit(f'{response.status_code} HTTP error.')

    json_data = json.loads(response.text)

    return json_data['results']


def get_previous_ads(search_name):
    previous_ads_filename = search_name_to_filename(search_name)
    if not isfile(previous_ads_filename) or os.stat(previous_ads_filename).st_size == 0:
        previous_ads = []
    else:
        with open(previous_ads_filename, 'r') as previous_ads_file:
            previous_ads = json.load(previous_ads_file)

    return previous_ads


def ad_is_new(ad, previous_ads):
    for previous_ad in previous_ads:
        if ad['id'] == previous_ad['id']:
            return False

    return True


def save_ads_to_file(new_ads, previous_ads, search_name):
    filename = search_name_to_filename(search_name)
    previous_ads = new_ads + previous_ads
    previous_ads = previous_ads[0:30]
    with open(filename, 'w')as previous_ads_file:
        json.dump(previous_ads, previous_ads_file, indent = 4)


def search_name_to_filename(search_name, file_extension='json'):
    filename = ''.join([c for c in search_name if c.isalpha() or c.isdigit() or c==' ']).rstrip()
    filename = filename.replace(' ', '_')
    return join(dirname(__file__), f'immo_ads-{filename}.{file_extension}')


def send_email(email_to, subject, body):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = EMAIL_FROM 
    msg['To'] = ', '.join(email_to)
    msg.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP(SMTP_HOSTNAME, SMTP_PORT)
    server.ehlo()
    server.starttls()
    server.login(SMTP_USERNAME, SMTP_PASSWORD)
    server.sendmail(EMAIL_FROM, email_to, msg.as_string())
    server.quit()
    

if __name__ == '__main__':
    main()

