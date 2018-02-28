#!/usr/bin/python
# -*- coding: utf-8 -*-
__author__ = "Sekiwere Samuel"

import requests
import json
import psycopg2
import psycopg2.extras
from settings import config
import phonenumbers
import getopt
import sys
import datetime

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'fd:',
    [])

now = datetime.datetime.now()
sdate = now - datetime.timedelta(days=1, minutes=5)
from_date = sdate.strftime('%Y-%m-%d %H:%M')

ADD_FIELDS = False

for option, parameter in opts:
    if option == '-d':
        from_date = parameter
    if option == '-f':
        ADD_FIELDS = True


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_request(url):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_available_fields():
    response = requests.get(
        '%sfields.json' % config['api_url'], headers={
            'Content-type': 'application/json',
            'Authorization': 'Token %s' % config['api_token']})
    results = [k['key'] for k in json.loads(response.text)['results']]
    return results


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    assert msisdn is not None
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)  # .replace('+', '')


def add_reporter_fields():
    our_fields = [
        {'label': 'facility', 'value_type': 'text'},
        {'label': 'facilitycode', 'value_type': 'text'},
        {'label': 'district', 'value_type': 'district'},
        {'label': 'Subcounty', 'value_type': 'text'},
        {'label': 'village', 'value_type': 'text'},
        {'label': 'reporting location', 'value_type': 'text'},
    ]
    fields = get_available_fields()
    for f in our_fields:
        if f['label'] not in fields:
            res = post_request(
                json.dumps(f), '%sfields.json' % config['api_url'])
            print res.text

if ADD_FIELDS:
    add_reporter_fields()
    sys.exit(1)
conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute(
    "SELECT id, lastname || ' ' || firstname as name, telephone, alternate_tel, "
    "email, get_location_name(district_id) AS district, role, "
    "facility, facilitycode, loc_name, created FROM reporters_view "
    "WHERE created >= %s", [from_date]
)

res = cur.fetchall()
print "==>", res
if res:
    for r in res:
        district = r["district"]
        fields = {
            "reporting_location": r['loc_name'],
            "facilitycode": r['facilitycode'],
            "facility": r['facility']
        }
        if district:
            fields["district"] = district
        phone = format_msisdn(r['telephone'])
        alt_phone = r['alternate_tel']
        if phone:
            data = {
                "name": r['name'],
                "urns": ["tel:" + phone],
                "email": r['email'],
                "groups": r['role'].split(','),
                "fields": fields
            }
            post_data = json.dumps(data)
            resp = post_request(post_data)
            # print post_data
            try:
                response_dict = json.loads(resp.text)
                print response_dict
                contact_uuid = response_dict["uuid"]
                cur.execute("UPDATE reporters SET uuid = %s WHERE id=%s", [contact_uuid, r["id"]])
                conn.commit()
            except:
                pass

            # print resp.text

        if alt_phone:
            alt_phone = format_msisdn(alt_phone)
            data["phone"] = alt_phone
            post_data = json.dumps(data)
            resp = post_request(post_data)
            # print resp.text
conn.close()
