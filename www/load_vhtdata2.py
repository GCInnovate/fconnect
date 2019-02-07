#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import getopt
import sys
# import requests
import datetime
from openpyxl import load_workbook
from settings import config
from settings import BASE_DIR
from app.tools.utils import format_msisdn, queue_schedule
from app.controllers import db

TEMPLATES_DIR = BASE_DIR + "/static/downloads/"

cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'f:d:u:h',
    ['upload-file', 'district', 'user'])


def usage():
    return """usage: python load_vhtdata.py [-f <excel-file>] [-d <district-name>] [-u <username>] [-h] [-a]
    -f path to input excel file to be imported
    -d district for the input excel file
    -u user account importing excel file
    -h Show this message
    """

user = "api_user"
upload_file = ""
district = ""
for option, parameter in opts:
    if option == '-f':
        upload_file = parameter
    if option == '-d':
        district = parameter.strip().capitalize()
    if option == '-u':
        user = parameter.strip()
    if option == '-h':
        print usage()
        sys.exit(1)

if not upload_file:
    print "An excel file is expected!"
    sys.exit(1)

order = {
    'role': 0, 'firstname': 1, 'lastname': 2, 'gender': 3, 'telephone': 4, 'alternate_tel': 5,
    'date_of_birth': 6, 'district': 7, 'subcounty': 8, 'facility': 9, 'facility_code': 10,
    'parish': 11, 'village': 12, 'nationalid': 13
}

print upload_file

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

current_time = datetime.datetime.now()

wb = load_workbook(upload_file, read_only=True)
print wb.get_sheet_names()
# get all the data in the different sheets
data = []
for sheet in wb:
    print sheet.title
    j = 0
    for row in sheet.rows:
        if j > 0:
            # val = ['%s' % i.value for i in row]
            val = [u'' if i.value is None else unicode(i.value) for i in row]
            # print val
            data.append(val)
        j += 1
print data
# start processing data in the sheets
for d in data:
    if not (d[order['firstname']] and d[order['telephone']] and d[order['facility']]):
        print "One of the mandatory fields (firstname, telephone or facility) missing"
        continue
    _firstname = d[order['firstname']].strip().capitalize()
    _lastname = d[order['lastname']].strip().capitalize()
    _role = d[order['role']].strip()
    if not _role:
        _role = 'VHT'
    _telephone = d[order['telephone']].strip()
    _alt_tel = d[order['alternate_tel']].strip()
    _gender = d[order['gender']].strip()
    _dob = d[order['date_of_birth']].strip()
    if _dob:
        try:
            _dob = datetime.strptime(_dob, "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d')
        except:
            _dob = ''
    urns = []
    alt_telephone = ""
    if _alt_tel:
        try:
            alt_telephone = format_msisdn(_alt_tel)
            urns.append("tel:" + alt_telephone)
        except:
            alt_telephone = ''
    if _telephone:
        try:
            telephone = format_msisdn(_telephone)
            urns.append("tel:" + telephone)
        except:
            telephone = ""

    # print "=====================>", _phone
    _district = d[order['district']].strip().capitalize()
    _subcounty = d[order['subcounty']].strip()
    _fac = d[order['facility']].strip()
    _parish = d[order['parish']].strip()
    _village = d[order['village']].strip()
    _nationalid = d[order['nationalid']].strip()
    _facility_code = d[order['facility_code']].strip()

    SQL = "SELECT id FROM chwr_reporters WHERE telephone like '%%%%%s%%%%' " % telephone
    if alt_telephone:
        SQL += " OR alternate_tel like '%%%%%s%%%%'" % alt_telephone

    res = db.query(SQL)

    if res:
        reporter_id = res[0]['id']
        db.query(
            "UPDATE chwr_reporters SET (firstname, lastname, telephone, alternate_tel) "
            " = ($firstname, $lastname, $telephone, $alternate_tel) "
            "WHERE id = $id", {
                'firstname': _firstname, 'lastname': _lastname,
                'telephone': telephone, 'alternate_tel': alt_telephone,
                'id': reporter_id
            })
    else:
        res = db.query(
            "INSERT INTO chwr_reporters(firstname, lastname, telephone, alternate_tel) "
            " VALUES ($firstname, $lastname, $telephone, $alternate_tel) RETURNING id", {
                'firstname': _firstname, 'lastname': _lastname,
                'telephone': telephone, 'alternate_tel': alt_telephone})
        if res:
            reporter_id = res[0]['id']

    contact_params = {
        'urns': urns,
        'name': _firstname + ' ' + _lastname,
        'fields': {
            # 'email': params.email,
            'gender': _gender,
            'registered_by': 'CHWR',
            'type': _role,
            'facility': _fac,
            'facilityuid': _facility_code,
            'district': _district,
            'sub_county': _subcounty,
            'parish': _parish,
            'village': _village,
            'reporter_id': reporter_id
        }
    }

    sync_time = current_time + datetime.timedelta(seconds=60)
    queue_schedule(db, contact_params, sync_time, None, 'push_contact', 0)

conn.close()
