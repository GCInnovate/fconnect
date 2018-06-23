#!/usr/bin/env python
import psycopg2
import psycopg2.extras
import json
import requests
import logging
from settings import config
from temba_client.v2 import TembaClient

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(process)d] %(levelname)-4s:  %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    filename='/tmp/fconnect_sched.log',
    filemode='a'
)

client = TembaClient(config.get('familyconnect_uri', 'http://localhost:8000/'), config['api_token'])

# To handle Json in DB well
psycopg2.extras.register_default_json(loads=lambda x: x)
psycopg2.extensions.register_adapter(dict, psycopg2.extras.Json)

conn = psycopg2.connect(
    "dbname=" + config["db_name"] + " host= " + config["db_host"] + " port=" + config["db_port"] +
    " user=" + config["db_user"] + " password=" + config["db_passwd"])
cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)


def post_request(data, url=config['default_api_uri']):
    response = requests.post(url, data=data, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def get_request(url=config['default_api_uri']):
    response = requests.get(url, headers={
        'Content-type': 'application/json',
        'Authorization': 'Token %s' % config['api_token']})
    return response


def sendsms(params):  # params has the sms params
    res = requests.get(config["smsurl"], params=params)
    return res.text


cur.execute(
    "SELECT id, params::text, type, reporter_id FROM schedules WHERE run_time "
    " <= current_timestamp "
    " AND status = 'ready' FOR UPDATE NOWAIT")
# FOR DEBUGGING
# cur.execute(
#     "SELECT id, params::text, type FROM schedules ORDER BY id DESC LIMIT 1")

res = cur.fetchall()
sched_len = len(res)
if sched_len:
    logging.info("Scheduler got %s SMS/URL/ContactPushes to send out" % sched_len)
for r in res:
    # cur.execute("SELECT id FROM schedules WHERE id = %s FOR UPDATE NOWAIT", [r["id"]])
    params = json.loads(r["params"])
    resp_text = ''
    try:
        if r['type'] == 'sms':
            response = sendsms(params)
            status = 'completed' if 'Accepted' in response else 'failed'
            cur.execute("UPDATE schedules SET status = %s WHERE id = %s", [status, r["id"]])
            conn.commit()
            logging.info(
                "Scheduler run: [schedid:%s] [status:%s] [msg:%s]" % (r["id"], status, params["text"]))
        elif r['type'] == 'push_contact':  # push RapidPro contacts
            payload = json.dumps(params)
            if r["reporter_id"]:
                cur.execute("SELECT uuid FROM reporters WHERE id = %s", [r["reporter_id"]])
                rpt = cur.fetchone()
                if rpt["uuid"]:
                    # here we update contact in rapidpro
                    resp = post_request(
                        payload, config["default_api_uri"] + "?uuid=" + rpt["uuid"])
                else:
                    resp = post_request(payload)
            else:
                # here we create contact in rapidpro
                resp = post_request(payload)
            # print resp.text
            resp_text = resp.text
            if resp.status_code in (200, 201, 203, 204):
                status = 'completed'
                response_dict = json.loads(resp.text)
                # print response_dict
                contact_uuid = response_dict["uuid"]
                if not rpt["uuid"]:
                    # update uuid for new contacts and start welcome flow
                    cur.execute(
                        "UPDATE reporters SET uuid = %s WHERE id=%s",
                        [contact_uuid, r["reporter_id"]])
                    try:
                        client.create_flow_start(
                            config['vht_registration_flow_uuid'],
                            contacts=[contact_uuid],
                            extra=params)
                    except:
                        pass
                    conn.commit()
            elif resp.status_code == 400:
                # perhaps already in familyconnect
                urn = params.get('urns', [])
                if urn:
                    tel = urn[0]
                    url = config['default_api_uri'] + "urn=%s" % tel
                    # print "YYY", url
                    resp2 = get_request(url)
                    xx = json.loads(resp2.text)
                    results = xx.get('results', '')
                    # print results
                    if results and len(results) < 2:
                        uuid = results[0].get('uuid', '')
                        # print uuid, tel
                        respx = post_request(payload, config['default_api_uri'] + "uuid=%s" % uuid)
                        status = 'completed'
                        logging.info(
                            "Scheduler run: contact update [schedid:%s] [tel: %s]" % (r["id"], tel))
                        cur.execute(
                            "UPDATE reporters SET uuid = %s WHERE id=%s",
                            [uuid, r["reporter_id"]])
                        try:
                            client.create_flow_start(
                                config['vht_registration_flow_uuid'],
                                contacts=[contact_uuid],
                                extra=params)
                        except:
                            pass
            else:
                status = 'failed'
            cur.execute("UPDATE schedules SET status = %s WHERE id = %s", [status, r["id"]])
            conn.commit()
            logging.info(
                "Scheduler run: [schedid:%s] [status:%s] [push_contacts:%s]" % (r["id"], status, params["urns"]))
    except Exception as e:
        logging.error("Scheduler Failed on [schedid:%s], [reason:%s] [resp:%s]" % (r["id"], str(e), resp_text))
conn.close()
