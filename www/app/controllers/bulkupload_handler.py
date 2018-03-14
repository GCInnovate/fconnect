import web
import os
import tempfile
import json
from . import db, require_login, render, get_session
from settings import BASE_DIR
UPLOAD_SCRIPT = BASE_DIR + "/load_vhtdata.py"


class BulkUpload:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
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

        l = locals()
        del l['self']
        return render.bulkupload(**l)

    @require_login
    def POST(self):
        params = web.input(uploadfile={}, caller='web', user='api_user', download="")
        # print "===>", params.keys()
        # print params.qquuid
        # print params.qqtotalfilesize
        # print params.qqfilename
        if params.download == 'VHT Template':
            session = get_session()
            if session.role == 'District User':
                district = session.username.capitalize()
                filename = '%s_Template.xlsx' % district
                fpath = "/static/downloads/" + filename
                web.header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheey')
                web.header('Content-disposition', 'attachment; filename=%s' % filename)
                web.seeother(fpath)

        if params.caller != 'api':
            session = get_session()
            username = session.username
            # userid = session.sesid
            role = session.role
        else:
            rs = db.query(
                "SELECT a.id, a.username, b.name as role "
                "FROM users a, user_roles b "
                "WHERE a.username = '%s' AND a.user_role = b.id" % params.user)
            if rs:
                user = rs[0]
                # userid = user['id']
                username = user['username']
                role = user['role']

        if role == 'District User':
            district = username.capitalize()
            f = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
            print f.name
            f.write(params.qqfile)
            cmd = UPLOAD_SCRIPT + " -f %s -d %s -u %s" % (f.name, district, username)
            try:
                f.close()
            except:
                pass
            print cmd
            os.popen(cmd)
            os.unlink(f.name)
            if params.caller == 'api':
                return json.dumps({'success': 'true', 'message': 'queued excel sheet for upload'})
            return json.dumps({'success': True})
        else:
            return json.dumps({
                "success": False,
                "error": "District login required for bulk upload", "preventRetry": True})
        return json.dumps({"success": False, "error": "error message to display", "preventRetry": True})
