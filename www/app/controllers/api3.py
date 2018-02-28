import json
import logging
import xlsxwriter
import difflib
from . import db
import web
from app.tools.utils import post_request
from settings import config
from app.tools.utils import get_basic_auth_credentials, auth_user

logging.basicConfig(
    format='%(asctime)s:%(levelname)s:%(message)s', filename='/tmp/fconnect-web.log',
    datefmt='%Y-%m-%d %I:%M:%S', level=logging.DEBUG
)


def find_closest_match(s, choice_list):
    r = difflib.get_close_matches(s, choice_list)
    return r[0] if r else []


class MatchSubcounty:
    """Matches Subcounties with those in DHIS 2, and updates the dhis2id field in locations table"""
    def GET(self):
        params = web.input(
            subcounty="", subcountyid="", districtid="", original_name="",
            username="", password=""
        )
        username = params.username
        password = params.password
        r = auth_user(db, username, password)
        if not r[0]:
            return "Unauthorized access"

        with db.transaction():
            res = db.query(
                "SELECT id FROM locations WHERE dhis2id = $dhis2id",
                {'dhis2id': params.districtid})
            if res:
                district_id = res[0]['id']
                synced = db.query(
                    "SELECT id FROM locations WHERE dhis2id = $dhis2id",
                    {'dhis2id': params.subcountyid})
                if synced:
                    # we already synced this one
                    # db.query(
                    #    "UPDATE locations SET name = $name WHERE dhis2id = $dhis2id",
                    #    {'name': params.original_name, 'dhis2id': params.subcountyid})
                    return "Subcounty already synced!"
                subcounties = {}
                res2 = db.query(
                    "SELECT id, name FROM locations WHERE tree_parent_id = $id",
                    {'id': district_id})
                for subcounty in res2:
                    subcounties[subcounty['name']] = subcounty['id']
                if params.subcounty in subcounties:
                    print "We have an exact match"
                    db.query(
                        "UPDATE locations SET dhis2id = $dhis2id WHERE id = $id",
                        {'dhis2id': params.subcountyid, 'id': subcounties[params.subcounty]})
                else:
                    print "We have to fuzzy match this one"
                    match_dict = {}
                    res3 = db.query(
                        "SELECT id, name FROM locations WHERE tree_parent_id = $id AND dhis2id = ''",
                        {'id': district_id})
                    for m in res3:
                        match_dict[m['name']] = m['id']
                    # match_list has those we want to try fuzzy matching with
                    choices = match_dict.keys()
                    matched_name = find_closest_match(params.original_name, choices)
                    if matched_name:
                        pmatch = difflib.SequenceMatcher(None, matched_name, params.subcounty).ratio()
                        # if pmatch > 0.84:
                        if pmatch > 0.9:
                            print "High match rate (%s%%) [%s => %s]" % ((pmatch * 100), params.original_name, matched_name)
                            db.query(
                                "UPDATE locations SET (dhis2id) = ($dhis2id) WHERE id = $id",
                                {
                                    'name': params.original_name, 'dhis2id':
                                    params.subcountyid, 'id': match_dict[matched_name]})
                        else:
                            print "Low mating rate (%s%%) [%s => %s]" % ((pmatch * 100), params.original_name, matched_name)
                    else:
                        print "Nothing appropriate to fuzzy match with for =>", params.subcounty
        return "Subcounty Sync Done."


class ReportersXLEndpoint:
    def GET(self):
        username, password = get_basic_auth_credentials()
        r = auth_user(db, username, password)
        if not r[0]:
            web.header("Content-Type", "application/json; charset=utf-8")
            web.header('WWW-Authenticate', 'Basic realm="Auth API"')
            web.ctx.status = '401 Unauthorized'
            return json.dumps({'detail': 'Authentication failed!'})
        web.header("Content-Type", "application/zip; charset=utf-8")
        # web.header('Content-disposition', 'attachment; filename=%s.csv'%file_name)


class ExcelTemplate:
    def GET(self):
        pass
