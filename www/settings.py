# -*- coding: utf-8 -*-

"""Default options for the application.
"""
import os

DEBUG = False

SESSION_TIMEOUT = 3600  # 1 Hour

HASH_KEY = ''
VALIDATE_KEY = ''
ENCRYPT_KEY = ''
SECRET_KEY = ''

PAGE_LIMIT = 25

SMS_OFFSET_TIME = 5
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def absolute(path):
    """Get the absolute path of the given file/folder.

    ``path``: File or folder.
    """
    PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(PROJECT_DIR, path))

config = {
    'db_name': 'fconnect',
    'db_host': 'localhost',
    'db_user': '',
    'db_passwd': '',
    'db_port': '5432',
    'logfile': '/tmp/mtrackpro-web.log',

    # DHIS2 Confs
    'dhis2_user': '',
    'dhis2_passwd': '',
    'base_url': 'http://hmis2.health.go.ug/api/analytics.csv?',
    'orgunits_url': 'http://hmis2.health.go.ug/api/organisationUnits',

    # sync_url is the service that creates/updates the facilities in mTracpro
    'sync_url': 'http://localhost:8080/create',
    'sync_user': 'admin',  # username for accessing sync service
    'sync_passwd': 'admin',  # password for sync service

    # facility levels as in DHIS 2 instance
    'levels': {
        'jTolsq2vJv8': 'HC II',
        'GM7GlqjfGAW': 'HC III',
        'luVzKLwlHJV': 'HC IV',
        'm0DN21c3PrY': 'General Hospital',
        'QEEIr51RGH8': 'NR Hospital',
        '2zEq4xZRpOp': 'RR Hospital',
        'YNsYaUOqAIs': 'Clinic',
    },

    'smsurl': 'http://localhost:13013/cgi-bin/sendsms?username=foo&password=bar',
    'default_api_uri': 'http://localhost:8000/api/v2/contacts.json',
    'api_token': 'c8cde9dbbdda6f544018e9321d017e909b28ec51',
    'api_url': 'http://localhost:8000/api/v2/',
    'vht_registration_flow_uuid': 'a974dae1-53bf-4eb6-bcd9-941c50b6b362',
    'familyconnect_uri': 'http://localhost:8000/',
    'reporters_upload_endpoint': 'http://localhost:8080/reportersupload'
}

# the order of fields in the reporter upload excel file
EXCEL_UPLOAD_ORDER = {
    'name': 0,
    'telephone': 1,
    'alternate_tel': 2,
    'role': 3,
    'subcounty': 4,
    'parish': 5,
    'village': 6,
    'village_code': 7
}

try:
    from local_settings import *
except ImportError:
    pass
