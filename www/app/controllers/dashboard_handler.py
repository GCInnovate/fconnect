import web
from . import db, require_login, render, get_session, allDistrictsByName


class Dashboard:
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
            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'VHT') = ANY (groups) "
                " AND district_id = $d", {'d': allDistrictsByName.get(session.username.capitalize(), 0)})
            total_vhts = r[0].count or 0

            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'Nurse') = ANY (groups) "
                " AND district_id = $d", {'d': allDistrictsByName.get(session.username.capitalize(), 0)})
            total_nurses = r[0].count or 0

            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'Midwife') = ANY (groups) "
                " AND district_id = $d", {'d': allDistrictsByName.get(session.username.capitalize(), 0)})
            total_midwives = r[0].count or 0
        else:
            districts_SQL = (
                "SELECT id, name FROM locations WHERE type_id = "
                "(SELECT id FROM locationtype WHERE name = 'district') ORDER by name")
            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'VHT') = ANY (groups);")
            total_vhts = r[0].count or 0

            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'Nurse') = ANY (groups);")
            total_nurses = r[0].count or 0

            r = db.query(
                "SELECT count(*) FROM reporters WHERE "
                "(SELECT id FROM reporter_groups WHERE name = 'Midwife') = ANY (groups);")
            total_midwives = r[0].count or 0

        districts = db.query(districts_SQL)
        district = {}

        l = locals()
        del l['self']
        return render.dashboard(**l)

    @require_login
    def POST(self):
        params = web.input(page="1", ed="", d_id="")
        session = get_session()
        if params.download == 'VHT Template':
            if session.role == 'District User':
                district = session.username.capitalize()
                filename = '%s_Template.xlsx' % district
                fpath = "/static/downloads/" + filename
                web.header('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheey')
                web.header('Content-disposition', 'attachment; filename=%s' % filename)
                web.seeother(fpath)
        l = locals()
        del l['self']
        return render.dashboard(**l)
