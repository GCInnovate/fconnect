# -*- coding: utf-8 -*-

"""Mako template options which are used, basically, by all handler modules in
controllers of the app.
"""

# from web.contrib.template import render_mako
import web
import datetime
from web.contrib.template import render_jinja
from settings import (absolute, config)

db_host = config['db_host']
db_name = config['db_name']
db_user = config['db_user']
db_passwd = config['db_passwd']
db_port = config['db_port']

db = web.database(
    dbn='postgres',
    user=db_user,
    pw=db_passwd,
    db=db_name,
    host=db_host,
    port=db_port
)

SESSION = ''
APP = None

ourDistricts = []
allDistricts = {}
allDistrictsByName = {}  # make use in pages easy
rs = db.query("SELECT id, name FROM  locations WHERE type_id = 3")
for r in rs:
    ourDistricts.append({'id': r['id'], 'name': r['name']})
    allDistricts[r['id']] = r['name']
    allDistrictsByName[r['name']] = r['id']

facilityLevels = {}
rs = db.query("SELECT id, name FROM healthfacility_type")
for r in rs:
    facilityLevels[r['id']] = r['name']

roles = []
rolesById = {}
rs = db.query("SELECT id, name from reporter_groups order by name")
for r in rs:
    roles.append({'id': r['id'], 'name': r['name']})
    rolesById[r['id']] = r['name']

userRolesByName = {}
rs = db.query("SELECT id, name from user_roles order by name")
for r in rs:
    userRolesByName[r['name']] = r['id']


def put_app(app):
    global APP
    APP = app


def get_app():
    global APP
    return APP


def get_session():
    global SESSION
    return SESSION


def datetimeformat(value, fmt='%Y-%m-%d'):
    if not value:
        return ''
    return value.strftime(fmt)


def facilityLevel(facilityid):
    return facilityLevels[facilityid]


def getDistrict(districtid):
    return allDistricts[districtid]


myFilters = {
    'datetimeformat': datetimeformat,
    'facilityLevel': facilityLevel,
    'getDistrict': getDistrict,
}

# Jinja2 Template options
render = render_jinja(
    absolute('app/views'),
    encoding='utf-8'
)

render._lookup.globals.update(
    ses=get_session(), roles=roles, year=datetime.datetime.now().strftime('%Y')
)
render._lookup.filters.update(myFilters)


def put_session(session):
    global SESSION
    SESSION = session
    render._lookup.globals.update(ses=session)


def csrf_token():
    session = get_session()
    if 'csrf_token' not in session:
        from uuid import uuid4
        session.csrf_token = uuid4().hex
    return session.csrf_token


def csrf_protected(f):
    def decorated(*args, **kwargs):
        inp = web.input()
        session = get_session()
        if not ('csrf_token' in inp and inp.csrf_token == session.pop('csrf_token', None)):
            raise web.HTTPError(
                "400 Bad request",
                {'content-type': 'text/html'},
                """Cross-site request forgery (CSRF) attempt (or stale browser form).
<a href="/"></a>.""")  # Provide a link back to the form
        return f(*args, **kwargs)
    return decorated

render._lookup.globals.update(csrf_token=csrf_token)


def require_login(f):
    """usage
    @require_login
    def GET(self):
        ..."""
    def decorated(*args, **kwargs):
        session = get_session()
        if not session.loggedin:
            session.logon_err = "Please Logon"
            return web.seeother("/")
        else:
            session.logon_err = ""
        return f(*args, **kwargs)

    return decorated
