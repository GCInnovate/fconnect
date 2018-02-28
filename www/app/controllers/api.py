import json
import web
from . import db
from app.tools.utils import get_basic_auth_credentials, auth_user


class LocationChildren:
    """Returns Children for a node """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM get_children($id) ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "name": r['name'],
                        "id": r['id'],
                        "attr": {'id': r['id']},
                        "parent": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class DistrictFacilities:
    """Returns facilities in a given district """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name FROM healthfacilities WHERE district_id = $id "
            "ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                ret.append(
                    {
                        "id": r['id'],
                        "name": r['name']
                    })
        return json.dumps(ret)


class LocationFacilities:
    """Returns facilities in a given location """
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name FROM healthfacilities WHERE location = $id "
            "ORDER BY name;", {'id': id})
        if rs:
            for r in rs:
                ret.append(
                    {
                        "id": r['id'],
                        "name": r['name']
                    })
        return json.dumps(ret)


class FacilityReporters:
    """Returns reports attached to a particular health facility"""
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT firstname, lastname, telephone FROM reporters WHERE id IN "
            "(SELECT reporter_id FROM reporter_healthfacility WHERE facility_id=$id) "
            " ORDER BY firstname, lastname",
            {'id': id})
        for r in rs:
            ret.append({
                "firstname": r['firstname'],
                "lastname": r['lastname'],
                "telephone": r['telephone']})
        return json.dumps(ret)


class Location:
    def GET(self, id):
        ret = []
        rs = db.query(
            "SELECT id, name, tree_parent_id FROM locations WHERE id = $id;", {'id': id})
        if rs:
            for r in rs:
                parent = r['tree_parent_id']
                ret.append(
                    {
                        "text": r['name'],
                        "attr": {'id': r['id']},
                        "id": parent if parent else "#",
                        "state": "closed"
                    })
        return json.dumps(ret)


class SubcountyLocations:
    def GET(self, id):
        """ returs the form bellow
        ret = {
            "Parish X": [{'name': "Villa 1"}, {"name": "Villa 2"}, {"name": "Villa 3"}],
            "Parish Y": [{'name': "Villa 4"}, {"name": "Villa 5"}],
            "Parish Z": [{'name': "Villa 6"}, {"name": "Villa 7"}],
        }
        """
        web.header("Content-Type", "application/json; charset=utf-8")
        ret = {}
        res = db.query("SELECT id, name FROM get_children($id)", {'id': id})
        for r in res:
            parish_name = r['name']
            parish_id = r['id']
            ret[parish_name] = []
            x = db.query("SELECT id, name FROM get_children($id)", {'id': parish_id})
            for i in x:
                ret[parish_name].append({'id': i['id'], 'name': i['name']})
        return json.dumps(ret)


class ReportersEndpoint:
    def GET(self, location_code):
        params = web.input(role="")
        web.header("Content-Type", "application/json; charset=utf-8")
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        ret = []
        reporter_role = params.role
        SQL = (
            "SELECT firstname, lastname, telephone, alternate_tel, email, national_id, "
            "reporting_location, district, role, loc_name, location_code FROM reporters_view4 "
            "WHERE reporting_location IN (SELECT id FROM get_descendants_including_self(( SELECT id FROM "
            "locations WHERE code=$location_code))) ")
        if reporter_role:
            SQL += " AND lower(role) = $role"
        res = db.query(SQL, {'location_code': location_code, 'role': reporter_role.lower()})
        if res:
            for r in res:
                ret.append({
                    "firstname": r.firstname, "lastname": r.lastname,
                    "telephone": r.telephone, "alternate_tel": r.alternate_tel,
                    "email": r.email, "national_id": r.national_id,
                    "location_name": r.loc_name,
                    "location_code": r.location_code,
                    "distrcit": r.district, "role": r.role
                })
        return json.dumps(ret)
