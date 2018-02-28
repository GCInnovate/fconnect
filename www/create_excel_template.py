import xlsxwriter
import psycopg2
import psycopg2.extras
from settings import config
from settings import BASE_DIR

TEMPLATES_DIR = BASE_DIR + "/static/downloads/"

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute("SELECT id, name FROM locations WHERE level = 2 ORDER BY name")
res = cur.fetchall()
for r in res[:2]:
    district_name = r['name']
    district_id = r['id']

    cur.execute("SELECT name FROM healthfacilities WHERE district_id = %s" % district_id)
    facilities = cur.fetchall()
    facility_list = []
    for f in facilities:
        facility_list.append('%s' % f['name'])

    cur.execute("select id, name from get_children(%s)" % district_id)
    subcounties = cur.fetchall()
    subcounty_list = []
    for s in subcounties:
        subcounty_list.append(s['name'])

    workbook = xlsxwriter.Workbook(TEMPLATES_DIR + "%s_Template.xlsx" % district_name.capitalize())
    worksheet = workbook.add_worksheet()

    bold = workbook.add_format({'bold': True})
    date_format = workbook.add_format({'num_format': 'yyyy-mm-d'})

    headings = [
        'Role', 'First Name', 'Last Name', 'Gender', 'Telephone', 'Other Telephone',
        'Date of Birth', 'Code', 'District', 'Subcounty', 'Heath Facility', 'Parish', 'Village'
    ]

    for idx, title in enumerate(headings):
        worksheet.write(0, idx, title, bold)

    worksheet.data_validation(1, 0, 1000, 0, {'validate': 'list', 'source': ['VHT', 'Nurse', 'Midwife']})
    worksheet.data_validation(1, 3, 1000, 3, {'validate': 'list', 'source': ['Female', 'Male']})
    worksheet.data_validation(1, 8, 1000, 8, {'validate': 'list', 'source': [district_name]})
    worksheet.data_validation(1, 9, 1000, 9, {'validate': 'list', 'source': subcounty_list})
    #worksheet.data_validation(1, 10, 1000, 10, {'validate': 'list', 'source': facility_list[:25]})

    workbook.close()

conn.close()
