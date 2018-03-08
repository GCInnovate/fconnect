import requests
import json
import web
import re
import base64
import phonenumbers
import simplejson
import psycopg2.extras
from settings import config


def format_msisdn(msisdn=None):
    """ given a msisdn, return in E164 format """
    assert msisdn is not None
    msisdn = msisdn.replace(' ', '')
    num = phonenumbers.parse(msisdn, getattr(config, 'country', 'UG'))
    is_valid = phonenumbers.is_valid_number(num)
    if not is_valid:
        return None
    return phonenumbers.format_number(
        num, phonenumbers.PhoneNumberFormat.E164)


def lit(**keywords):
    return keywords


def get_webhook_msg(params, label='msg'):
    """Returns value of given lable from rapidpro webhook data"""
    values = json.loads(params['values'])  # only way we can get out Rapidpro values in webpy
    msg_list = [v.get('value') for v in values if v.get('label') == label]
    if msg_list:
        msg = msg_list[0].strip()
        if msg.startswith('.'):
            msg = msg[1:]
        return msg
    return ""


def default(*args):
    p = [i for i in args if i or i == 0]
    if p.__len__():
        return p[0]
    if args.__len__():
        return args[args.__len__() - 1]
    return None


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def auth_user(db, username, password):
    sql = (
        "SELECT a.id, a.firstname, a.lastname, b.name as role "
        "FROM users a, user_roles b "
        "WHERE username = $username AND password = crypt($passwd, password) "
        "AND a.user_role = b.id AND is_active = 't'")
    res = db.query(sql, {'username': username, 'passwd': password})
    if not res:
        return False, "Wrong username or password"
    else:
        return True, res[0]


def audit_log(db, log_dict={}):
    sql = (
        "INSERT INTO audit_log (logtype, actor, action, remote_ip, detail, created_by) "
        " VALUES ($logtype, $actor, $action, $ip, $descr, $user) "
    )
    db.query(sql, log_dict)
    return None


def get_basic_auth_credentials():
    auth = web.ctx.env.get('HTTP_AUTHORIZATION')
    if not auth:
        return (None, None)
    auth = re.sub('^Basic ', '', auth)
    username, password = base64.decodestring(auth).split(':')
    return username, password


def get_location_role_reporters(db, location_id, roles=[], include_alt=True):
    """Returns a contacts list of reporters of specified roles attached to a location
    include_alt allows to add alternate telephone numbers to returned list
    """
    SQL = (
        "SELECT telephone, alternate_tel FROM reporters_view2 WHERE "
        "role IN (%s) " % ','.join(["'%s'" % i for i in roles]))
    SQL += " AND reporting_location = $location"
    res = db.query(SQL, {'location': location_id})
    ret = []
    if res:
        for r in res:
            telephone = r['telephone']
            alternate_tel = r['alternate_tel']
            if telephone:
                ret.append(format_msisdn(telephone))
            if alternate_tel and include_alt:
                ret.append(format_msisdn(alternate_tel))
    return list(set(ret))


def queue_schedule(db, params, run_time, user=None, stype='sms', reporter=None):  # params has the text, recipients and other params
    res = db.query(
        "INSERT INTO schedules (params, run_time, type, created_by, reporter_id) "
        " VALUES($params, $runtime, $type, $user, $reporter) RETURNING id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'type': stype,
            'reporter': reporter
        })
    if res:
        return res[0]['id']
    return None


def update_queued_sms(db, sched_id, params, run_time, user=None):
    db.query(
        "UPDATE schedules SET params=$params, run_time=$runtime, updated_by=$user, "
        " status='ready', updated=now() WHERE id=$id",
        {
            'params': psycopg2.extras.Json(params, dumps=simplejson.dumps),
            'runtime': run_time,
            'user': user,
            'id': sched_id
        })


def log_schedule(db, distribution_log_id, sched_id, level, triggered_by=1):
    db.query(
        "INSERT INTO distribution_log_schedules(distribution_log_id, schedule_id, level, triggered_by) "
        "VALUES($log_id, $sched_id, $level, $triggered_by)", {
            'log_id': distribution_log_id, 'sched_id': sched_id,
            'level': level, 'triggered_by': triggered_by})


def get_request(url):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response
