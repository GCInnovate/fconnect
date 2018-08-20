import web
import json
import datetime
import simplejson
import psycopg2.extras
from . import csrf_protected, db, require_login, get_session, render, allDistrictsByName
from . import rolesById
from app.tools.utils import audit_log, default, lit, queue_schedule, format_msisdn
from app.tools.pagination2 import doquery, countquery, getPaginationString
from settings import PAGE_LIMIT


class Reporters:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="", caller="web", search="", show="")
        edit_val = params.ed
        search_field = params.search
        show = params.show
        session = get_session()
        if session.role == 'District User':
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') "
                "AND name = '%s'" % session.username.capitalize())
        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")

        districts = db.query(districts_SQL)
        district = {}
        roles = db.query("SELECT id, name from reporter_groups order by name")
        allow_edit = False

        try:
            edit_val = int(params.ed)
            allow_edit = True
        except ValueError:
            pass
        try:
            page = int(params.page)
        except:
            page = 1
        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        if params.ed and allow_edit:
            res = db.query(
                "SELECT id, firstname, lastname, gender, telephone, "
                "reporting_location, role, alternate_tel, facilityid, facility, code, date_of_birth, "
                "national_id, created, loc_name FROM reporters_view1 "
                " WHERE id = $id", {'id': edit_val})
            if res:
                r = res[0]
                reporter_id = edit_val
                firstname = r.firstname
                lastname = r.lastname
                gender = r.gender
                telephone = r.telephone
                national_id = r.national_id
                role = r.role.split(',')
                alt_telephone = r.alternate_tel
                location = r.reporting_location
                parish = ""
                subcounty = ""
                facilityid = r.facilityid
                facility = r.facility
                facilityname = r.facility
                code = r.code
                date_of_birth = r.date_of_birth
                district = ""
                village = ""
                villagename = r.loc_name
                subcounties = []
                ancestors = db.query(
                    "SELECT id, name, level FROM get_ancestors($loc) "
                    "WHERE level > 1 ORDER BY level DESC;", {'loc': location})
                if ancestors:
                    for loc in ancestors:
                        if loc['level'] == 4:
                            parish = loc
                            parishname = loc['name']
                            villages = db.query(
                                "SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        if loc['level'] == 3:
                            subcounty = loc
                            subcountyname = loc['name']
                            parishes = db.query(
                                "SELECT id, name FROM get_children($id)", {'id': loc['id']})
                        elif loc['level'] == 2:
                            district = loc
                            districtname = loc['name']
                            subcounties = db.query(
                                "SELECT id, name FROM get_children($id)", {'id': loc['id']})
                else:
                    district = location
                location_for_facilities = subcounty.id if subcounty else district.id

                if location_for_facilities:
                    facilities = db.query(
                        "SELECT id, name FROM healthfacilities WHERE location=$loc",
                        {'loc': location_for_facilities})
                if facilityid:
                    facility = r.facility

        allow_del = False
        try:
            del_val = int(params.d_id)
            allow_del = True
        except ValueError:
            pass
        if params.d_id and allow_del:
            if session.role in ('District User', 'Administrator'):
                reporter = db.query(
                    "SELECT firstname || ' ' || lastname as name, telephone "
                    "FROM reporters WHERE id = $id", {'id': params.d_id})
                if reporter:
                    rx = reporter[0]
                    log_dict = {
                        'logtype': 'Web', 'action': 'Delete', 'actor': session.username,
                        'ip': web.ctx['ip'], 'descr': 'Deleted reporter %s:%s (%s)' % (
                            params.d_id, rx['name'], rx['telephone']),
                        'user': session.sesid
                    }
                    # db.query("DELETE FROM reporter_groups_reporters WHERE reporter_id=$id", {'id': params.d_id})
                    # db.query("DELETE FROM reporter_healthfacility WHERE reporter_id=$id", {'id': params.d_id})
                    db.query("DELETE FROM schedules WHERE reporter_id=$id", {'id': params.d_id})
                    db.query("DELETE FROM reporters WHERE id=$id", {'id': params.d_id})
                    audit_log(db, log_dict)
                    if params.caller == "api":  # return json if API call
                        web.header("Content-Type", "application/json; charset=utf-8")
                        return json.dumps({'message': "success"})

        if session.role == 'District User':
            district_id = allDistrictsByName['%s' % session.username.capitalize()]
            criteria = "district_id=%s" % district_id
            if params.search:
                criteria += (
                    " AND (telephone ilike '%%%%%s%%%%' OR alternate_tel ilike '%%%%%s%%%%' OR "
                    "name ilike '%%%%%s%%%%')")
                criteria = criteria % (params.search, params.search, params.search)
                dic = lit(
                    relations='reporters_view1',
                    fields=(
                        "id, name, gender, telephone, district_id, alternate_tel, "
                        "facility, role, uuid, created "),
                    criteria=criteria,
                    order="facility, name",
                    limit=limit, offset=start)
            else:
                dic = lit(
                    relations='reporters_view1',
                    fields=(
                        "id, name, gender, telephone, district_id, alternate_tel, "
                        "facility, role,  uuid, created "),
                    criteria=criteria,
                    order="id desc",
                    limit=limit, offset=start)
        else:
            criteria = "TRUE "
            if params.search:
                criteria += (
                    " AND (telephone ilike '%%%%%s%%%%' OR alternate_tel ilike '%%%%%s%%%%' OR "
                    "name ilike '%%%%%s%%%%')")
                criteria = criteria % (params.search, params.search, params.search)
                dic = lit(
                    relations='reporters_view1',
                    fields=(
                        "id, name, gender, telephone, district_id, alternate_tel, "
                        "facility, role, uuid, created "),
                    criteria=criteria,
                    order="facility, name",
                    limit=limit, offset=start)
            else:
                criteria = "id >  (SELECT max(id) - 250 FROM reporters)"
                dic = lit(
                    relations='reporters_view1',
                    fields=(
                        "id, name, gender, telephone, district_id, alternate_tel, "
                        "facility, role, uuid, created "),
                    criteria=criteria,
                    order="facility, name",
                    limit=limit, offset=start)

        try:
            reporters = doquery(db, dic)
            count = countquery(db, dic)
        except:
            reporters = []
            count = 0
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "reporters", "?page=")
        l = locals()
        del l['self']
        return render.reporters(**l)

    # @csrf_protected
    @require_login
    def POST(self):
        params = web.input(
            firstname="", lastname="", gender="", telephone="", email="", location="",
            role="", alt_telephone="", page="1", ed="", d_id="", district="", facility="",
            code="", date_of_birth="", national_id="", caller="", user="api_user", districtname="",
            subcounty="", parish="",
            subcountyname="", parishname="", villagename="", facilityname="")
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
        facilityuid = ""
        rs = db.query("SELECT code FROM healthfacilities WHERE id = %s;" % params.facility)
        if rs:
            facilityuid = rs[0]['code']

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
        contact_params = {
            'urns': urns,
            'name': params.firstname + ' ' + params.lastname,
            # 'groups': ['%s' % rolesById[int(params.role)]],
            'fields': {
                # 'email': params.email,
                'gender': params.gender,
                'facility': params.facilityname,
                'village': params.villagename,
                'district': params.districtname,
                'sub_county': params.subcountyname,
                'parish': params.parishname,
                'facilityuid': facilityuid,
                'type': '%s' % rolesById[int(params.role)]
            }
        }

        with db.transaction():
            if params.ed and allow_edit:
                location = params.location if params.location else None
                date_of_birth = params.date_of_birth if params.date_of_birth else None
                r = db.query(
                    "UPDATE reporters SET firstname=$firstname, lastname=$lastname, gender=$gender, "
                    "telephone=$telephone, reporting_location=$location, "
                    "alternate_tel=$alt_tel, district_id = $district_id, facilityid=$facility, "
                    "code=$code, date_of_birth=$date_of_birth, national_id=$national_id "
                    "WHERE id=$id RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'gender': params.gender, 'telephone': params.telephone,
                        'location': location, 'id': params.ed,
                        'alt_tel': params.alt_telephone, 'district_id': params.district,
                        'code': params.code, 'date_of_birth': date_of_birth,
                        'national_id': params.national_id, 'facility': params.facility
                    })
                if r:
                    db.query(
                        "UPDATE reporters SET groups = $groups::INTEGER[], "
                        " jparents = $ancestors WHERE id = $id",
                        {
                            'id': params.ed,
                            'groups': str([int(params.role)]).replace(
                                '[', '{').replace(']', '}').replace('\'', '\"'),
                            'ancestors': psycopg2.extras.Json({
                                'd': params.district,
                                's': params.subcounty,
                                'p': params.parish}, dumps=simplejson.dumps)
                        }
                    )

                    log_dict = {
                        'logtype': 'Web', 'action': 'Update', 'actor': username,
                        'ip': web.ctx['ip'],
                        'descr': 'Updated reporter %s:%s (%s)' % (
                            params.ed, params.firstname + ' ' + params.lastname, params.telephone),
                        'user': userid
                    }
                    audit_log(db, log_dict)

                    sync_time = current_time + datetime.timedelta(seconds=60)
                    queue_schedule(db, contact_params, sync_time, userid, 'push_contact', params.ed)
                if params.caller == 'api':
                    web.header("Content-Type", "application/json; charset=utf-8")
                    return json.dumps({'message': 'Reporter edited successfully.'})

                else:
                    return web.seeother("/reporters")
            else:
                location = params.location if params.location else None
                has_reporter = db.query(
                    "SELECT id FROM reporters WHERE telephone = $tel", {'tel': params.telephone})
                if has_reporter:
                    if params.caller == 'api':
                        web.header("Content-Type", "application/json; charset=utf-8")
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
                    " district_id, code, date_of_birth, national_id, facilityid) VALUES "
                    " ($firstname, $lastname, $gender, $telephone, $location, "
                    " $alt_tel, $district_id, $code, $date_of_birth, $national_id, $facilityid) RETURNING id", {
                        'firstname': params.firstname, 'lastname': params.lastname,
                        'gender': params.gender, 'telephone': params.telephone,
                        'location': location, 'alt_tel': params.alt_telephone,
                        'district_id': params.district, 'code': params.code,
                        'date_of_birth': params.date_of_birth if params.date_of_birth else None,
                        'national_id': params.national_id, 'facilityid': params.facility
                    })
                if r:
                    reporter_id = r[0]['id']

                    db.query(
                        "UPDATE reporters SET groups = $groups::INTEGER[], "
                        " jparents = $ancestors WHERE id = $id",
                        {
                            'id': reporter_id,
                            'groups': str([int(params.role)]).replace(
                                '[', '{').replace(']', '}').replace('\'', '\"'),
                            'ancestors': psycopg2.extras.Json({
                                'd': params.district,
                                's': params.subcounty,
                                'p': params.parish}, dumps=simplejson.dumps)
                        }
                    )

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
                    web.header("Content-Type", "application/json; charset=utf-8")
                    return json.dumps({'message': 'success'})
                else:
                    return web.seeother("/reporters?show=true")

        l = locals()
        del l['self']
        if params.caller == 'api':
            pass
        else:
            return render.reporters(**l)
