-- mTrac Tables, Samuel Sekiwere, 2017-02-25
-- remeber to add indexes
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION "uuid-ossp";
CREATE EXTENSION plpythonu;
CREATE EXTENSION hstore;

-- webpy sessions
CREATE TABLE sessions (
    session_id CHAR(128) UNIQUE NOT NULL,
    atime TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data TEXT
);

CREATE TABLE user_roles (
    id SERIAL NOT NULL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    descr text DEFAULT '',
    cdate TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX user_roles_idx1 ON user_roles(name);

CREATE TABLE user_role_permissions (
    id SERIAL NOT NULL PRIMARY KEY,
    user_role INTEGER NOT NULL REFERENCES user_roles ON DELETE CASCADE ON UPDATE CASCADE,
    Sys_module TEXT NOT NULL, -- the name of the module - defined above this level
    sys_perms VARCHAR(16) NOT NULL,
    unique(sys_module,user_role)
);

CREATE TABLE users (
    id bigserial NOT NULL PRIMARY KEY,
    user_role  INTEGER NOT NULL REFERENCES user_roles ON DELETE RESTRICT ON UPDATE CASCADE, --(call agents, admin, service providers)
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL UNIQUE,
    telephone TEXT NOT NULL DEFAULT '', -- acts as the username
    password TEXT NOT NULL, -- blowfish hash of password
    email TEXT NOT NULL DEFAULT '',
    allowed_ips TEXT NOT NULL DEFAULT '127.0.0.1;::1', -- semi-colon separated list of allowed ip masks
    denied_ips TEXT NOT NULL DEFAULT '', -- semi-colon separated list of denied ip masks
    failed_attempts TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    transaction_limit TEXT DEFAULT '0/'||to_char(now(),'yyyymmdd'),
    is_active BOOLEAN NOT NULL DEFAULT 't',
    is_system_user BOOLEAN NOT NULL DEFAULT 'f',
    last_login TIMESTAMPTZ,
    last_passwd_update TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX users_idx1 ON users(telephone);
CREATE INDEX users_idx2 ON users(username);

CREATE TABLE audit_log (
        id BIGSERIAL NOT NULL PRIMARY KEY,
        logtype VARCHAR(32) NOT NULL DEFAULT '',
        actor TEXT NOT NULL,
        action text NOT NULL DEFAULT '',
        remote_ip INET,
        detail TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id), -- like actor id
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX au_idx1 ON audit_log(created);
CREATE INDEX au_idx2 ON audit_log(logtype);
CREATE INDEX au_idx4 ON audit_log(action);

CREATE TABLE configs (
        id serial NOT NULL PRIMARY KEY,
        item TEXT NOT NULL UNIQUE,
        val TEXT NOT NULL,
        detail TEXT DEFAULT '',
        created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION gen_code() RETURNS TEXT AS
$delim$
import string
import random
from uuid import uuid4


def id_generator(size=12, chars=string.ascii_lowercase + string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

return id_generator()
$delim$ LANGUAGE plpythonu;

CREATE TABLE locationtree(
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL DEFAULT '',
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP

);


CREATE TABLE locationtype(
    id SERIAL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    name TEXT NOT NULL DEFAULT '',
    level INTEGER NOT NULL,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE locations(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    tree_id INTEGER NOT NULL REFERENCES locationtree(id),
    type_id INTEGER NOT NULL REFERENCES locationtype(id), --Cascade
    code TEXT NOT NULL DEFAULT gen_code(),
    name TEXT NOT NULL DEFAULT '',
    tree_parent_id INTEGER REFERENCES locations(id),
    lft INTEGER NOT NULL,
    rght INTEGER NOT NULL,
    dhis2id TEXT NOT NULL DEFAULT '',
    level INTEGER,
    cdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX locations_idx4 ON locations(lft);
CREATE INDEX locations_idx5 ON locations(rght);
CREATE INDEX locations_idx6 ON locations(code);

CREATE VIEW locations_view AS
    SELECT a.*, b.level FROM locations a, locationtype b
    WHERE a.type_id = b.id;

--FUNCTIONS
CREATE OR REPLACE FUNCTION public.get_children(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
    BEGIN
        FOR r IN SELECT * FROM locations_view WHERE tree_parent_id = loc_id
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;


CREATE OR REPLACE FUNCTION public.get_descendants(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft > our_lft AND rght < our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_descendants_including_self(loc_id bigint)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft >= our_lft AND rght <= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION public.get_ancestors(loc_id integer)
 RETURNS SETOF locations_view AS
$delim$
     DECLARE
        r locations_view%ROWTYPE;
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations_view WHERE id = loc_id;
        FOR r IN SELECT * FROM locations_view WHERE lft <= our_lft AND rght >= our_rght
        LOOP
            RETURN NEXT r;
        END LOOP;
        RETURN;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION add_node(treeid INT, node_name TEXT, p_id INT) RETURNS BOOLEAN AS --p_id = id of node where to add
$delim$
    DECLARE
    new_lft INTEGER;
    lvl INTEGER;
    dummy TEXT;
    node_type INTEGER;
    child_type INTEGER;
    BEGIN
        IF node_name = '' THEN
            RAISE NOTICE 'Node name cannot be empty string';
            RETURN FALSE;
        END IF;
        SELECT level INTO lvl FROM locationtype WHERE id = (SELECT type_id FROM locations WHERE id = p_id);
        IF NOT FOUND THEN
            RAISE EXCEPTION 'Cannot add node: failed to find level';
        END IF;
        SELECT rght, type_id INTO new_lft, node_type FROM locations WHERE id =  p_id AND tree_id = treeid;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'No such node id= % ', p_id;
        END IF;

        SELECT id INTO child_type FROM locationtype WHERE level = lvl + 1 AND tree_id = tree_id;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'You cannot add to root node';
        END IF;

        SELECT name INTO dummy FROM locations WHERE name = node_name
            AND tree_id = treeid AND type_id = child_type AND tree_parent_id = p_id;
        IF FOUND THEN
            RAISE NOTICE 'Node already exists : %', node_name;
            RETURN FALSE;
        END IF;

        UPDATE locations SET lft = lft + 2 WHERE lft > new_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght + 2 WHERE rght >= new_lft AND tree_id = treeid;
        INSERT INTO locations (name, lft, rght, tree_id,type_id, tree_parent_id)
        VALUES (node_name, new_lft, new_lft+1, treeid, child_type, p_id);
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION delete_node(treeid INT, node_id BIGINT)
    RETURNS boolean AS $delim$
    DECLARE
        node_lft INTEGER;
    BEGIN
        SELECT lft INTO node_lft FROM locations
            WHERE id = node_id AND tree_id = treeid;
        IF NOT FOUND THEN RETURN FALSE; END IF;
        UPDATE locations SET lft = lft - 2 WHERE lft > node_lft AND tree_id = treeid;
        UPDATE locations SET rght = rght - 2 WHERE rght > node_lft AND tree_id = treeid;
        DELETE FROM locations WHERE id = node_id;
        RETURN TRUE;
    END;
$delim$ LANGUAGE plpgsql;

CREATE TABLE orgunit_groups(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    dhis2id TEXT NOT NULL DEFAULT '',
    cdate TIMESTAMP DEFAULT NOW()
);

-- this is used for synchronizing with DHIS2
CREATE TABLE facilities(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    dhis2id TEXT NOT NULL DEFAULT '',
    district TEXT NOT NULL DEFAULT '',
    is_033b BOOLEAN DEFAULT 'f',
    level TEXT NOT NULL DEFAULT '',
    subcounty TEXT NOT NULL DEFAULT '',
    cdate TIMESTAMP DEFAULT NOW(),
    ldate TIMESTAMP DEFAULT NOW()
);

CREATE TABLE healthfacility_type(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT UNIQUE NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE healthfacilities(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    type_id INTEGER NOT NULL REFERENCES healthfacility_type(id),
    name TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '', --dhis2id
    district_id BIGINT REFERENCES locations,
    district TEXT NOT NULL DEFAULT '',
    location BIGINT REFERENCES locations(id), --subcounty
    location_name TEXT NOT NULL DEFAULT '', -- these are done for performance reasons
    is_033b BOOLEAN DEFAULT 't',
    last_reporting_date DATE,
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX healthfacilities_idx ON healthfacilities(code);
CREATE INDEX healthfacilities_idx1 ON healthfacilities(district);

CREATE TABLE reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    uuid TEXT NOT NULL DEFAULT '', -- this is the rapidpro uuid
    firstname TEXT NOT NULL DEFAULT '',
    lastname TEXT NOT NULL DEFAULT '',
    gender TEXT NOT NULL DEFAULT '',
    telephone TEXT NOT NULL DEFAULT '',
    alternate_tel TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    date_of_birth DATE,
    reporting_location BIGINT REFERENCES locations(id), --village
    district_id BIGINT REFERENCES locations,
    reporting_location_name text not null default '',
    created_by INTEGER REFERENCES users(id), -- like actor id
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX reporters_idx1 ON reporters(telephone);
CREATE INDEX reporters_idx2 ON reporters(alternate_tel);
CREATE INDEX reporters_idx3 ON reporters(created);
CREATE INDEX reporters_idx4 ON reporters(district_id);
CREATE INDEX reporters_idx5 ON reporters(uuid);

CREATE TABLE reporter_healthfacility(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    reporter_id BIGINT NOT NULL REFERENCES reporters(id),
    facility_id BIGINT REFERENCES healthfacilities(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporter_groups(
    id SERIAL PRIMARY KEY NOT NULL,
    name TEXT NOT NULL DEFAULT '',
    descr TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE reporter_groups_reporters(
    id BIGSERIAL NOT NULL PRIMARY KEY,
    group_id INTEGER REFERENCES reporter_groups(id),
    reporter_id BIGINT REFERENCES reporters(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE  dhis2_mtrack_indicators_mapping(
    id SERIAL PRIMARY KEY NOT NULL,
    form TEXT NOT NULL DEFAULT '', -- mTrac Form e.g cases, death
    slug TEXT NOT NULL DEFAULT '', -- command variable in mTrac
    cmd TEXT NOT NULL DEFAULT '', -- mTrac commands e.g ma, ch, tf
    form_order INTEGER, -- order they appear in case of HTML form generation
    description TEXT NOT NULL DEFAULT '',
    dataset TEXT NOT NULL DEFAULT '',
    dataelement TEXT NOT NULL DEFAULT '',
    category_combo TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx ON dhis2_mtrack_indicators_mapping(form);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx1 ON dhis2_mtrack_indicators_mapping(slug);
CREATE INDEX dhis2_mtrack_indicators_mapping_idx3 ON dhis2_mtrack_indicators_mapping(dataelement);

-- used for scheduling messages
CREATE TABLE schedules(
    id SERIAL PRIMARY KEY NOT NULL,
    type TEXT NOT NULL DEFAULT 'sms', -- also 'push_contact'
    params JSON NOT NULL DEFAULT '{}'::json,
    run_time TIMESTAMP NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'ready',
    created_by INTEGER REFERENCES users(id),
    updated_by INTEGER REFERENCES users(id),
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX schedules_idx ON schedules(run_time);
CREATE INDEX schedules_idx1 ON schedules(type);
CREATE INDEX schedules_idx2 ON schedules(status);

CREATE TABLE alerts(
    id BIGSERIAL PRIMARY KEY NOT NULL,
    district_id BIGINT REFERENCES locations(id),
    reporting_location BIGINT REFERENCES locations(id),
    alert TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    created TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE kannel_stats(
    id SERIAL PRIMARY KEY NOT NULL,
    month TEXT NOT NULL DEFAULT '',
    stats JSON NOT NULL DEFAULT '{}'::json,
    created TIMESTAMP NOT NULL DEFAULT NOW(),
    updated TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE VIEW sms_stats AS
    SELECT
        id,
        month,
        stats->>'mtn_in' as mtn_in,
        stats->>'mtn_out' as mtn_out,
        stats->>'airtel_in' as airtel_in,
        stats->>'airtel_out' as airtel_out,
        stats->>'africel_in' as africel_in,
        stats->>'africel_out' as africel_out,
        stats->>'utl_in' as utl_in,
        stats->>'utl_out' as utl_out,
        stats->>'others_in' as others_in,
        stats->>'others_out' as others_out,
        stats->>'total_in' as total_in,
        stats->>'total_out' as total_out,
        created,
        updated
    FROM kannel_stats;


INSERT INTO user_roles(name, descr)
VALUES
    ('Administrator','For the Administrators'),
    ('District Users', 'For the district users'),
    ('Partners', 'The partners'), ('API Users', 'The API users');

INSERT INTO user_role_permissions(user_role, sys_module,sys_perms)
VALUES
        ((SELECT id FROM user_roles WHERE name ='Administrator'),'Users','rw');

INSERT INTO users(firstname,lastname,username,telephone,password,email,user_role,is_system_user)
VALUES
        ('Samuel','Sekiwere','admin', '+256782820208', crypt('admin',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Administrator'),'t'),
        ('Guest','User','guest', '+256753475676', crypt('guest',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='District Users'),'t'),
        ('api', 'user', 'api_user', '', crypt('api',gen_salt('bf')), 'a@example.com',
        (SELECT id FROM user_roles WHERE name ='API Users'), 't'),
        ('Ivan','Muguya','ivan', '+256756253430', crypt('ivan',gen_salt('bf')),'sekiskylink@gmail.com',
        (SELECT id FROM user_roles WHERE name ='Partners'),'f');

INSERT INTO reporter_groups (name, descr)
VALUES
    ('VHT', 'Village Health Team Members'),
    ('HC', 'Health Workers'),
    ('', ''),
    ('DHO', 'District Health Officer'),
    ('', '');

INSERT INTO healthfacility_type(name) values
    ('HC II'), ('HC III'), ('HC IV'), ('General Hospital'), ('NR Hospital'), ('RR Hospital'), ('Clinic');

CREATE OR REPLACE FUNCTION public.get_district(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name into r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_district_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'district');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_subcounty_id(loc_id bigint)
 RETURNS bigint
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r BIGINT;
        our_lft BIGINT;
        our_rght BIGINT;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT id INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = 'subcounty');
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_ancestor_by_type(loc_id bigint, atype text)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
     DECLARE
        r TEXT := '';
        our_lft INTEGER;
        our_rght INTEGER;
    BEGIN
        SELECT lft, rght INTO our_lft, our_rght FROM locations WHERE id = loc_id;
        SELECT name INTO r FROM locations WHERE lft <= our_lft AND rght >= our_rght AND
            type_id=(SELECT id FROM locationtype WHERE name = atype);
        RETURN r;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_location_name(loc_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
        xname TEXT;
    BEGIN
        SELECT INTO xname name FROM locations WHERE id = loc_id;
        IF xname IS NULL THEN
            RETURN '';
        END IF;
        RETURN xname;
    END;
$function$;

CREATE OR REPLACE FUNCTION public.get_reporter_groups(_reporter_id bigint)
 RETURNS text
 LANGUAGE plpgsql
AS $function$
    DECLARE
    r TEXT;
    p TEXT;
    BEGIN
        r := '';
        FOR p IN SELECT name FROM reporter_groups WHERE id IN
            (SELECT group_id FROM reporter_groups_reporters WHERE reporter_id = _reporter_id) LOOP
            r := r || p || ',';
        END LOOP;
        RETURN rtrim(r,',');
    END;
$function$;

DROP VIEW IF EXISTS reporters_view;
CREATE VIEW reporters_view AS
    SELECT a.id, a.firstname, a.lastname, a.firstname || ' ' || a.lastname as name,
        a.gender, a.telephone, a.alternate_tel, a.email,
        a.reporting_location, a.created_by, a.district_id, a.uuid, a.code, a.date_of_birth,
        get_reporter_groups(a.id) as role, a.created, b.name as loc_name,
        b.code as location_code, d.name as facility, c.facility_id as facilityid, d.code as facilitycode
    FROM reporters a, locations b, reporter_healthfacility c, healthfacilities d
    WHERE a.reporting_location = b.id AND (a.id = c.reporter_id AND d.id = c.facility_id);
