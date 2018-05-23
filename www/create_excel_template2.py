import xlsxwriter
import psycopg2
import psycopg2.extras
import getopt
import sys
from datetime import date
from settings import config
from settings import BASE_DIR


cmd = sys.argv[1:]
opts, args = getopt.getopt(
    cmd, 'd:h',
    ['district'])


def usage():
    return """usage: python create_excel_template2.py [-d <district-name>] [-h]
    -d district for which to generate excel template
    -h Show this message
    """

SQL = "SELECT id, name FROM locations WHERE level = 2 "

for option, parameter in opts:
    if option == '-d':
        district = parameter.strip().capitalize()
        if district:
            SQL += "AND name='%s' " % district
    if option == '-h':
        print usage()
        sys.exit(1)

SQL += " ORDER BY name"

TEMPLATES_DIR = BASE_DIR + "/static/downloads/"

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

# cur.execute("SELECT id, name FROM locations WHERE level = 2 ORDER BY name")
cur.execute(SQL)

res = cur.fetchall()
for r in res:
    district_name = r['name']
    district_id = r['id']
    workbook = xlsxwriter.Workbook(
        TEMPLATES_DIR + "%s_Template.xlsx" % district_name.capitalize(), {'default_date_format': 'dd/mm/yyyy'})
    # set some formats
    text_format = workbook.add_format()
    text_format.set_num_format('@')
    text_format.set_font_size(14)
    date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    date_format.set_font_size(14)
    bold = workbook.add_format({'bold': True})
    bold.set_font_size(14)

    cur.execute("select id, name from get_children(%s)" % district_id)
    subcounties = cur.fetchall()
    subcounty_list = []
    for s in subcounties:
        subcounty_name = s["name"]
        subcountyid = s["id"]
        subcounty_list.append(s['name'])

        cur.execute("SELECT name FROM healthfacilities WHERE location = %s" % subcountyid)
        facilities = cur.fetchall()
        facility_list = []
        for f in facilities:
            facility_list.append('%s' % f['name'])

        worksheet = workbook.add_worksheet(subcounty_name)

        headings = [
            'Role', 'First Name', 'Last Name', 'Gender', 'Telephone', 'Other Telephone',
            'Date of Birth', 'Code', 'District', 'Subcounty', 'Health Facility', 'Parish', 'Village',
            'National ID'
        ]

        for idx, title in enumerate(headings):
            worksheet.write(0, idx, title, bold)

        worksheet.data_validation(1, 0, 1000, 0, {
            'validate': 'list', 'source': ['VHT', 'Nurse', 'Midwife'],
            'error_title': 'Role Invalid', 'error_message': 'Role should either be VHT, Nurse or Midwife'})
        worksheet.data_validation(1, 3, 1000, 3, {'validate': 'list', 'source': ['Female', 'Male']})
        worksheet.data_validation(1, 8, 1000, 8, {'validate': 'list', 'source': [district_name]})
        worksheet.data_validation(1, 9, 1000, 9, {'validate': 'list', 'source': [subcounty_name]})
        worksheet.data_validation(1, 10, 1000, 10, {'validate': 'list', 'source': facility_list[:25]})
        worksheet.set_column("A:A", 10, text_format)
        worksheet.set_column("B:C", 15, text_format)
        worksheet.set_column("D:D", 10, text_format)
        worksheet.set_column("B:C", 15, text_format)
        worksheet.set_column("E:F", 17, text_format)
        worksheet.set_column("G:G", 15, date_format)
        worksheet.set_column("H:N", 15, text_format)
        worksheet.write_comment('A1', 'Role should either be VHT, Nurse or Midwife', {'visible': False})
        worksheet.write_comment('G1', 'Birthday should be of the form DD Month YYY.\n eg 20 April 1980', {'visible': False})
        # worksheet.data_validation(1, 6, 1000, 6, {
        #     'validate': 'date', 'criteria': 'between',
        #     'minimum': date(1952, 1, 1), 'maximum': date(2001, 12, 12),
        #     'error_title': 'Birthday is invalid', 'error_message': 'Birthday should be between 1952 and 2001!'})
        worksheet.conditional_format(1, 6, 1000, 6, {
            'type': 'date', 'criteria': 'between', 'minimum': date(1952, 1, 1),
            'maximum': date(2001, 12, 12), 'format': date_format,
        })
        # worksheet.data_validation(1, 9, 1000, 9, {'validate': 'list', 'source': subcounty_list})
        # worksheet.data_validation(1, 10, 1000, 10, {'validate': 'list', 'source': facility_list[:25]})

    workbook.close()

conn.close()
