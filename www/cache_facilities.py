import psycopg2
import psycopg2.extras
import requests
import json
from settings import config


def get_url(url):
    res = requests.get(url, params=payload, auth=(user, passwd))
    return res.text

user = config["dhis2_user"]
passwd = config["dhis2_passwd"]

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])

cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

cur.execute(
    "SELECT dhis2id, name FROM locations WHERE type_id = "
    "(SELECT id FROM locationtype WHERE name = 'district')")

URL = "%s.json?level=5;%s&fields=id,name&paging=false"  # % config["orgunits_url"]

districts = cur.fetchall()
for d in districts:
    if not d["dhis2id"]:
        continue
    url_to_call = URL % (config["orgunits_url"], d["dhis2id"])
    print url_to_call

    payload = {}

    response = get_url(url_to_call)
    orgunits_dict = json.loads(response)
    orgunits = orgunits_dict['organisationUnits']

    for orgunit in orgunits:
        cur.execute("SELECT id FROM facilities WHERE dhis2id = %s", (orgunit["id"],))
        res = cur.fetchone()
        if not res:  # we don't have an entry already
            cur.execute(
                "INSERT INTO facilities(name, dhis2id) VALUES (%s, %s)",
                (orgunit["name"], orgunit["id"]))
            print "NEW ==>", orgunit["id"]
        else:  # we have the entry
            cur.execute(
                "UPDATE facilities SET name = %s WHERE dhis2id = %s",
                (orgunit["name"], orgunit["id"]))
        conn.commit()
conn.close()
