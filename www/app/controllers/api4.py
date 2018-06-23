import web
import json
import datetime
from . import db, get_session, render
from . import rolesById
from app.tools.utils import audit_log, queue_schedule, format_msisdn


class ReportersAPI:
    def POST(self):
        params = web.input(
            firstname="", lastname="", gender="", telephone="", email="", location="",
            role="", alt_telephone="", page="1", ed="", d_id="", district="", facility="",
            code="", date_of_birth="", caller="", user="api_user", national_id="",
            facilityname="", districtname="", subcounty="", parish="", village="")
        if params.caller != 'api':
            session = get_session()
            username = session.username
            userid = session.sesid
        else:
            rs = db.query("SELECT id, username FROM users WHERE username = '%s';" % params.user)
            if rs:
                xuser = rs[0]
                userid = xuser['id']
                username = xuser['username']

        allow_edit = False
        try:
            edit_val = int(params.ed)
            allow_edit = True
        except:
            pass
        current_time = datetime.datetime.now()
        # Set params to schedule a push_contact to Push reporter to RapidPro
        urns = []
        if params.alt_telephone:
            try:
                alt_telephone = format_msisdn(params.alt_telephone)
                urns.append("tel:" + alt_telephone)
            except:
                alt_telephone = ''
        if params.telephone:
            try:
                telephone = format_msisdn(params.telephone)
                urns.append("tel:" + telephone)
            except:
                telephone = ''
        groups = ['%s' % rolesById[int(i)] for i in params.role]
        rtype = groups[0] if groups else 'VHT'
        contact_params = {
            'urns': urns,
            'name': params.firstname + ' ' + params.lastname,
            # 'groups': ['Type = %s' % rolesById[int(i)] for i in params.role],
            'fields': {
                # 'email': params.email,
                'gender': params.gender,
                'registered_by': 'Portal v2',
                'type': rtype,
                'facility': params.facilityname,
                'facilityuid': '',
                'district': params.districtname,
                'sub_county': params.subcounty,
                'parish': params.parish,
                'village': params.village
            }
        }

        with db.transaction():
            if params.ed and allow_edit:
                location = params.location if params.location else None
                r = db.query(
                    "UPDATE reporters SET firstname=$firstname, lastname=$lastname, gender=$gender, "
                    "telephone=$telephone, reporting_location=$location, "
                    "alternate_tel=$alt_tel, district_id = $district_id, "
                    "code=$code, date_of_birth=$date_of_birth, "
                    "national_id=$national_id "
                    "WHERE id=$id RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'gender': params.gender, 'telephone': params.telephone,
                        'location': location, 'id': params.ed,
                        'alt_tel': params.alt_telephone, 'district_id': params.district,
                        'code': params.code, 'date_of_birth': params.date_of_birth,
                        'national_id': params.national_id
                    })
                if r:
                    for group_id in params.role:
                        rx = db.query(
                            "SELECT id FROM reporter_groups_reporters "
                            "WHERE reporter_id = $id AND group_id =$gid ",
                            {'gid': group_id, 'id': params.ed})
                        if not rx:
                            db.query(
                                "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                                " VALUES ($group_id, $reporter_id)",
                                {'group_id': group_id, 'reporter_id': params.ed})
                    # delete other groups
                    db.query(
                        "DELETE FROM reporter_groups_reporters WHERE "
                        "reporter_id=$id AND group_id NOT IN $roles",
                        {'id': params.ed, 'roles': params.role})

                    log_dict = {
                        'logtype': 'Web', 'action': 'Update', 'actor': username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated reporter %s:%s (%s)' % (
                            params.ed, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': userid
                    }
                    audit_log(db, log_dict)

                    sync_time = current_time + datetime.timedelta(seconds=60)
                    if urns:  # only queue if we have numbers
                        queue_schedule(db, contact_params, sync_time, userid, 'push_contact', params.ed)
                return web.seeother("/reporters")
            else:
                location = params.location if params.location else None
                has_reporter = db.query(
                    "SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.telephone})
                if has_reporter:
                    reporterid = has_reporter[0]["id"]
                    rx = db.query(
                        "UPDATE reporters SET firstname=$firstname, lastname=$lastname, gender=$gender, "
                        "telephone=$telephone, reporting_location=$location, "
                        "alternate_tel=$alt_tel, district_id = $district_id, "
                        "code=$code, date_of_birth=$date_of_birth, "
                        "national_id=$national_id "
                        "WHERE id=$id RETURNING id", {
                            'firstname': params.firstname, 'lastname': params.lastname,
                            'gender': params.gender, 'telephone': params.telephone,
                            'location': location, 'id': reporterid,
                            'alt_tel': params.alt_telephone, 'district_id': params.district,
                            'code': params.code,
                            'date_of_birth': params.date_of_birth if params.date_of_birth else None,
                            'national_id': params.national_id
                        })
                    sync_time = current_time + datetime.timedelta(seconds=60)
                    queue_schedule(db, contact_params, sync_time, userid, 'push_contact', reporterid)

                    if params.caller == 'api':
                        return json.dumps({
                            'message': "Reporter with Telephone:%s already registered" % params.telephone})
                    else:
                        session.rdata_err = (
                            "Reporter with Telephone:%s already registered" % params.telephone
                        )
                        return web.seeother("/reporters")
                if params.caller != 'api':
                    session.rdata_err = ""
                r = db.query(
                    "INSERT INTO reporters (firstname, lastname, gender, telephone, "
                    " reporting_location, alternate_tel, "
                    " district_id, code, date_of_birth, national_id) VALUES "
                    " ($firstname, $lastname, $gender, $telephone, $location, "
                    " $alt_tel, $district_id, $code, $date_of_birth, $national_id) RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'gender': params.gender, 'telephone': params.telephone,
                        'location': location, 'alt_tel': params.alt_telephone,
                        'district_id': params.district, 'code': params.code,
                        'date_of_birth': params.date_of_birth if params.date_of_birth else None,
                        'national_id': params.national_id
                    })
                if r:
                    reporter_id = r[0]['id']
                    db.query(
                        "INSERT INTO reporter_healthfacility (reporter_id, facility_id) "
                        "VALUES($reporter_id, $facility_id)",
                        {'reporter_id': reporter_id, 'facility_id': params.facility})
                    for group_id in params.role:
                        db.query(
                            "INSERT INTO reporter_groups_reporters (group_id, reporter_id) "
                            " VALUES ($role, $reporter_id)",
                            {'role': group_id, 'reporter_id': reporter_id})
                    log_dict = {
                        'logtype': 'Web', 'action': 'Create', 'actor': username,
                        'ip': web.ctx['ip'],
                        'descr': 'Created reporter %s:%s (%s)' % (
                            reporter_id, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': userid
                    }
                    audit_log(db, log_dict)

                    sync_time = current_time + datetime.timedelta(seconds=60)
                    queue_schedule(db, contact_params, sync_time, userid, 'push_contact', reporter_id)
                if params.caller == 'api':
                    return json.dumps({'message': 'success'})
                else:
                    return web.seeother("/reporters?show=true")

        l = locals()
        del l['self']
        if params.caller == 'api':
            pass
        else:
            return render.reporters(**l)
