#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import getopt
import sys
import requests
from datetime import datetime
from openpyxl import load_workbook
from settings import config
from settings import BASE_DIR

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
    'date_of_birth': 6, 'code': 7, 'district': 8, 'subcounty': 9, 'facility': 10,
    'parish': 11, 'village': 12, 'nationalid': 13
}

print upload_file

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

rolesByName = {}
cur.execute("SELECT id, name FROM reporter_groups")
rs = cur.fetchall()
for r in rs:
    rolesByName[r['name']] = r['id']

allDistrictsByName = {}
cur.execute("SELECT id, name FROM  locations WHERE type_id = 3")
rs = cur.fetchall()
for r in rs:
    allDistrictsByName[r['name']] = r['id']

# load subcounties in district. Plus facilities per subcounty
subcountiesByName = {}
subcountyFacilitiesByName = {}  # {subcountyid: {facilityname: facilityid, ....}}
subcountyParishesByName = {}  # {subcountyid: {parishname: parishid, ...}}
subcountyVillagesByName = {}  # {subcountyid: {villagename: villageid, ...}}
cur.execute(
    "SELECT id, name FROM locations WHERE tree_parent_id = %s",
    [allDistrictsByName[district.capitalize()]])
rs = cur.fetchall()
for r in rs:
    subcountiesByName[r['name']] = r['id']
    subcountyFacilitiesByName[r['id']] = {}
    cur.execute(
        "SELECT id, name FROM healthfacilities WHERE location = %s", [r['id']])
    subcounty_facilities = cur.fetchall()
    for facility in subcounty_facilities:
        subcountyFacilitiesByName[r['id']][facility['name']] = facility['id']

    subcountyParishesByName[r['id']] = {}
    cur.execute("SELECT id, name FROM get_children(%s)", [r['id']])
    subcounty_parishes = cur.fetchall()
    for parish in subcounty_parishes:
        subcountyParishesByName[r['id']][parish['name']] = parish['id']

    subcountyVillagesByName[r['id']] = {}
    cur.execute("SELECT id, name FROM get_descendants(%s) where type_id = 6", [r['id']])
    subcounty_villages = cur.fetchall()
    for village in subcounty_villages:
        subcountyVillagesByName[r['id']][village['name']] = village['id']

import pprint
pprint.pprint(subcountyFacilitiesByName)

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
    _firstname = d[order['firstname']].strip()
    _lastname = d[order['lastname']].strip()
    _role = d[order['role']].strip()
    if not _role:
        _role = 'VHT'
    _telephone = d[order['telephone']].strip()
    _alt_tel = d[order['alternate_tel']].strip()
    _code = d[order['code']].strip()
    _gender = d[order['gender']].strip()
    _dob = d[order['date_of_birth']].strip()
    if _dob:
        try:
            _dob = datetime.strptime(_dob, "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d')
        except:
            _dob = ''
    # print "=====================>", _phone
    _district = d[order['district']].strip()
    districtid = allDistrictsByName[district.capitalize()]
    _subcounty = d[order['subcounty']].strip()
    _fac = d[order['facility']].strip()
    _parish = d[order['parish']].strip()
    _village = d[order['village']].strip()
    _nationalid = d[order['nationalid']].strip()
    if _subcounty and _subcounty in subcountiesByName:
        subcountyid = subcountiesByName[_subcounty]
        if subcountyid and _fac:
            location = subcountyid
            parishname = ""
            villagename = ""
            if _parish:
                parish_loc = 0
                try:
                    parish_loc = subcountyParishesByName[subcountyid][_parish]
                    if parish_loc:
                        parishname = _parish
                        # location = parish_loc
                except:
                    pass
            if _village:
                try:
                    village_loc = subcountyVillagesByName[subcountyid][_village]
                    if village_loc:
                        villagename = _village
                        # location = village_loc
                except:
                    pass
            try:
                facilityid = subcountyFacilitiesByName[subcountyid][_fac]
            except:
                print "Facility ID for [%s]could not be got" % _fac, "subcountyid:", subcountyid
                continue
            print "WE CAN ADD THIS ONE YEY!"
            params = {
                'firstname': _firstname, 'lastname': _lastname, 'gender': _gender,
                'telephone': _telephone, 'alt_telephone': _alt_tel, 'role': rolesByName[_role],
                'district': districtid, 'facility': facilityid, 'location': subcountyid,
                'caller': 'api', 'date_of_birth': _dob, 'code': _code, 'user': user,
                'national_id': _nationalid, "facilityname": _fac,
                'subcounty': _subcounty,
                'parish': parishname, 'village': villagename,
                'districtname': district}
            try:
                import pprint
                pprint.pprint(params)
                requests.post(config.get(
                    'reporters_upload_endpoint',
                    'http://localhost:8080/reportersupload'), data=params)
            except:
                pass

conn.close()
