import web
from . import csrf_protected, db, require_login, render, get_session
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class FSync:
    @require_login
    def GET(self):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        session = get_session()
        try:
            page = int(params.page)
        except:
            page = 1

        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0
        if session.role == 'District User':
            criteria = "district='%s'" % session.username.capitalize()
        else:
            criteria = ""
        dic = lit(
            relations='facilities', fields="id, name, dhis2id, district, subcounty, is_033b, level, ldate",
            criteria=criteria,
            order="district, subcounty, name asc",
            limit=limit, offset=start)
        facilities = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "fsync", "?page=")

        l = locals()
        del l['self']
        return render.fsync(**l)

    @csrf_protected
    @require_login
    def POST(self):
        params = web.input(page="1", ed="", d_id="", abtn="", fid=[])
        try:
            page = int(params.page)
        except:
            page = 1

        with db.transaction():
            if params.abtn == 'Sync Selected':
                if params.fid:
                    for val in params.fid:
                        pass
                db.transaction().commit()
                return web.seeother("/fsync")
            if params.abtn == 'Full Sync':
                if params.fid:
                    for val in params.fid:
                        pass
                db.transaction().commit()
                return web.seeother("/fsync")

        l = locals()
        del l['self']
        return render.fsync(**l)
