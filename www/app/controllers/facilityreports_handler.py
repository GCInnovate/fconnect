import web
from . import csrf_protected, db, require_login, render
from app.tools.pagination2 import doquery, countquery, getPaginationString
from app.tools.utils import default, lit
from settings import PAGE_LIMIT


class FacilityReports:
    @require_login
    def GET(self, facilitycode):
        params = web.input(page=1, ed="", d_id="")
        edit_val = params.ed
        try:
            page = int(params.page)
        except:
            page = 1

        limit = PAGE_LIMIT
        start = (page - 1) * limit if page > 0 else 0

        dic = lit(
            relations='requests_view',
            fields="id, facility, facility_name, district, msisdn, body, raw_msg, year, week, created",
            criteria="facility='%s'" % facilitycode,
            order="id desc",
            limit=limit, offset=start)

        reports = doquery(db, dic)
        count = countquery(db, dic)
        pagination_str = getPaginationString(default(page, 0), count, limit, 2, "ready", "?page=")

        l = locals()
        del l['self']
        return render.facilityreports(**l)
