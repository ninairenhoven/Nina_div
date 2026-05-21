import os
import re
import time
import json
import sqlite3
import requests
from datetime import date, timedelta
from urllib.parse import quote as url_quote
from concurrent.futures import ThreadPoolExecutor, as_completed
from flask import Flask, send_from_directory, Response, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY       = os.getenv('EVENTOR_API_KEY')
BASE_URL      = 'https://eventor.orientering.no/api'
TIME4O_BASE   = 'https://center.time4o.com/api/v1'
LIVERES_BASE  = 'https://api.liveres.live/api.php'
RATASS_BASE   = 'https://o.fjoven.com'
MY_PERSON_ID  = os.getenv('EVENTOR_PERSON_ID', '45234')
TRACKED_IDS   = os.getenv('EVENTOR_TRACKED_IDS', MY_PERSON_ID)

LIVERES_STATUS = {
    '0': 'OK',
    '1': 'DidNotStart',
    '2': 'DidNotFinish',
    '3': 'Disqualified',
    '4': 'MissingPunch',
    '10': 'Active',
}

DB_PATH   = os.path.join(os.path.dirname(__file__), 'cache.db')
CACHE_TTL = 1800  # 30 minutes


# ── SQLite cache ────────────────────────────────────────────────────────────────

def _db():
    con = sqlite3.connect(DB_PATH)
    con.execute('''
        CREATE TABLE IF NOT EXISTS cache (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            cached_date TEXT NOT NULL,
            expires_at REAL NOT NULL
        )
    ''')
    con.execute('''
        CREATE TABLE IF NOT EXISTS livelinks (
            event_id TEXT PRIMARY KEY,
            race_id  TEXT NOT NULL,
            verified TEXT NOT NULL DEFAULT 'unverified'
        )
    ''')
    con.execute('''
        CREATE TABLE IF NOT EXISTS pinned_events (
            event_id TEXT PRIMARY KEY,
            name     TEXT NOT NULL,
            date     TEXT NOT NULL
        )
    ''')
    con.execute('''
        CREATE TABLE IF NOT EXISTS pinned_runners (
            name TEXT PRIMARY KEY
        )
    ''')
    con.execute("ALTER TABLE livelinks ADD COLUMN verified TEXT NOT NULL DEFAULT 'unverified'"
                ) if 'verified' not in [r[1] for r in con.execute('PRAGMA table_info(livelinks)').fetchall()] else None
    con.commit()
    return con


def _cache_get(key):
    today = date.today().isoformat()
    now   = time.time()
    try:
        with _db() as con:
            row = con.execute(
                'SELECT value, cached_date, expires_at FROM cache WHERE key = ?', (key,)
            ).fetchone()
        if row and row[1] == today and row[2] > now:
            return row[0]
    except Exception as e:
        app.logger.warning('cache_get failed for %s: %s', key, e)
    return None


def _cache_set(key, value, ttl=CACHE_TTL):
    today = date.today().isoformat()
    now   = time.time()
    try:
        with _db() as con:
            con.execute('''
                INSERT INTO cache (key, value, cached_date, expires_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value      = excluded.value,
                    cached_date = excluded.cached_date,
                    expires_at  = excluded.expires_at
            ''', (key, value, today, now + ttl))
    except Exception as e:
        app.logger.warning('cache_set failed for %s: %s', key, e)


# ── Eventor helpers ─────────────────────────────────────────────────────────────

def eventor_get(path):
    return requests.get(
        f'{BASE_URL}{path}',
        headers={'ApiKey': API_KEY},
        timeout=15,
    )


def _merge_starts_for_all():
    from_date = (date.today() - timedelta(days=60)).isoformat()
    to_date   = (date.today() + timedelta(days=7)).isoformat()

    all_items = []
    for pid in TRACKED_IDS.split(','):
        pid = pid.strip()
        try:
            r = eventor_get(f'/starts/person?personId={pid}&fromDate={from_date}&toDate={to_date}')
            if r.ok:
                all_items.extend(re.findall(r'<StartList\b[^>]*>.*?</StartList>', r.text, re.DOTALL))
        except Exception as e:
            app.logger.warning('starts/person failed for %s: %s', pid, e)

    return ''.join(all_items)


def _fetch_class_map(event_ids):
    """Returns {EventClassId: ClassName} for the given event IDs, fetched in parallel."""
    class_map = {}

    def fetch_one(eid):
        try:
            r = eventor_get(f'/eventclasses?eventId={eid}')
            if r.ok:
                result = {}
                for m in re.finditer(r'<EventClass\b[^>]*>(.*?)</EventClass>', r.text, re.DOTALL):
                    cid   = re.search(r'<EventClassId>(\d+)</EventClassId>', m.group(1))
                    cname = re.search(r'<Name>([^<]+)</Name>', m.group(1))
                    if cid and cname:
                        result[cid.group(1)] = cname.group(1)
                return result
        except Exception as e:
            app.logger.warning('eventclasses failed for %s: %s', eid, e)
        return {}

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(fetch_one, eid) for eid in event_ids]
        for fut in as_completed(futures):
            class_map.update(fut.result())
    return class_map


def _inject_class_names(entry_items, class_map):
    """Add <Class><Name>...</Name></Class> to each entry based on its EntryClass/EventClassId."""
    enriched = []
    for item in entry_items:
        m = re.search(r'(<EntryClass[^>]*>.*?<EventClassId>(\d+)</EventClassId>.*?</EntryClass>)',
                      item, re.DOTALL)
        if m and m.group(2) in class_map:
            esc = class_map[m.group(2)].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            item = item.replace(m.group(1), m.group(1) + f'<Class><Name>{esc}</Name></Class>', 1)
        enriched.append(item)
    return enriched


def _get_events_xml():
    cached = _cache_get('events')
    if cached:
        app.logger.info('Returning events XML from cache')
        return cached

    app.logger.info('Cache miss — fetching from Eventor')
    xml = ('<?xml version="1.0" encoding="utf-8"?><StartListList>'
           + _merge_starts_for_all()
           + '</StartListList>')
    _cache_set('events', xml)
    return xml


# ── liveres.live helpers ────────────────────────────────────────────────────────

def _liveres_raceinfo(comp):
    """Fetch liveres.live page and parse title for name + date."""
    resp = requests.get(f'https://liveres.live/followfull.php?comp={comp}', timeout=15)
    resp.raise_for_status()
    m = re.search(r'<title>[^<]*::\s*([^[<]+?)\s*\[(\d{4}-\d{2}-\d{2})\]', resp.text)
    if m:
        return {'name': m.group(1).strip(), 'date': m.group(2)}
    return {}


def _liveres_results(comp):
    """Fetch all class results from liveres.live and normalize to time4o entry format."""
    classes_resp = requests.get(f'{LIVERES_BASE}?comp={comp}&method=getclasses', timeout=15)
    classes_resp.raise_for_status()
    class_names = [c['className'] for c in classes_resp.json().get('classes', [])]

    def fetch_class(cls_name):
        r = requests.get(
            f'{LIVERES_BASE}?comp={comp}&method=getclassresults'
            f'&class={url_quote(cls_name)}&unformattedTimes=true&nosplits=true',
            timeout=15,
        )
        r.raise_for_status()
        return cls_name, r.json()

    entries = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_class, c): c for c in class_names}
        for fut in as_completed(futures):
            try:
                cls_name, data = fut.result()
                for runner in data.get('results', []):
                    status_raw = str(runner.get('status', '0'))
                    status_str = LIVERES_STATUS.get(status_raw, 'OK')
                    cs = runner.get('result')
                    start_cs = runner.get('start') or 0
                    try:
                        cs_int = int(cs)
                        time_ms = cs_int * 10 if cs_int > 0 else None
                    except (TypeError, ValueError):
                        cs_int = 0
                        time_ms = None
                    finish_hhmm = None
                    if time_ms is not None and start_cs:
                        finish_s = (int(start_cs) + cs_int) / 100
                        finish_hhmm = f'{int(finish_s // 3600):02d}:{int((finish_s % 3600) // 60):02d}'
                    time_obj = None
                    if time_ms is not None:
                        time_obj = {'time': time_ms}
                        if finish_hhmm:
                            time_obj['finishHHMM'] = finish_hhmm
                    entries.append({
                        'person': {'name': runner.get('name', ''), 'club': runner.get('club', '')},
                        'class': cls_name,
                        'status': {'status': status_str},
                        'time': time_obj,
                        'position': runner.get('place'),
                        'start': runner.get('start'),
                    })
            except Exception as e:
                app.logger.warning('liveres fetch_class failed for %s: %s', futures[fut], e)
    return entries


# ── Routes ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    resp = send_from_directory('cloudflare', 'index.html')
    resp.headers['Cache-Control'] = 'no-cache, must-revalidate'
    return resp


@app.route('/my-events')
def my_events():
    return Response(_get_events_xml(), status=200, mimetype='application/xml')


@app.route('/startlist')
def startlist():
    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')
    cache_key = f'startlist:{event_id}'
    cached = _cache_get(cache_key)
    if cached:
        app.logger.info('Returning startlist for %s from cache', event_id)
        return Response(cached, status=200, mimetype='application/xml')
    app.logger.info('Cache miss — fetching startlist for %s from Eventor', event_id)
    resp = eventor_get(f'/starts/event?eventId={event_id}')
    if resp.ok:
        _cache_set(cache_key, resp.text, ttl=21600)  # 6 hours
        return Response(resp.text, status=200, mimetype='application/xml')
    app.logger.warning('Eventor startlist %s: HTTP %s — %s', event_id, resp.status_code, resp.text[:200])
    msg = 'Startliste ikke publisert ennå' if resp.status_code == 404 else f'Eventor feil {resp.status_code}'
    return Response(json.dumps({'error': msg}), status=resp.status_code, mimetype='application/json')


@app.route('/entries')
def entries():
    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')
    cache_key = f'entries:{event_id}'
    cached = _cache_get(cache_key)
    if cached:
        app.logger.info('Returning entries for %s from cache', event_id)
        return Response(cached, status=200, mimetype='application/xml')
    app.logger.info('Cache miss — fetching entries for %s from Eventor', event_id)
    resp = eventor_get(
        f'/entries?eventIds={event_id}&includePersonElement=true&includeOrganisationElement=true'
    )
    if resp.ok:
        entry_items = re.findall(r'<Entry\b[^>]*>.*?</Entry>', resp.text, re.DOTALL)
        class_map   = _fetch_class_map({event_id})
        enriched    = ''.join(_inject_class_names(entry_items, class_map))
        xml = re.sub(r'(<EntryList\b[^>]*>).*?(</EntryList>)',
                     lambda m: m.group(1) + enriched + m.group(2),
                     resp.text, flags=re.DOTALL)
        _cache_set(cache_key, xml, ttl=1800)
        return Response(xml, status=200, mimetype='application/xml')
    app.logger.warning('Eventor entries %s: HTTP %s — %s', event_id, resp.status_code, resp.text[:200])
    msg = 'Påmeldingsliste ikke tilgjengelig' if resp.status_code == 404 else f'Eventor feil {resp.status_code}'
    return Response(json.dumps({'error': msg}), status=resp.status_code, mimetype='application/json')


@app.route('/pinned-events', methods=['GET', 'POST', 'DELETE'])
def pinned_events():
    if request.method == 'GET':
        with _db() as con:
            rows = con.execute(
                'SELECT event_id, name, date FROM pinned_events ORDER BY date'
            ).fetchall()
        return Response(
            json.dumps([{'id': r[0], 'name': r[1], 'date': r[2]} for r in rows]),
            status=200, mimetype='application/json'
        )

    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')

    if request.method == 'DELETE':
        with _db() as con:
            con.execute('DELETE FROM pinned_events WHERE event_id = ?', (event_id,))
        return Response('{}', status=200, mimetype='application/json')

    # POST — fetch event info from Eventor and store
    try:
        resp = eventor_get(f'/event/{event_id}')
        if not resp.ok:
            return Response('{"error":"Løp ikke funnet"}', status=404, mimetype='application/json')
        name_m = re.search(r'<Name>([^<]+)</Name>', resp.text)
        date_m = re.search(r'<StartDate>.*?<Date>([^<]+)</Date>', resp.text, re.DOTALL)
        name = name_m.group(1) if name_m else f'Løp {event_id}'
        ev_date = date_m.group(1) if date_m else ''
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')

    with _db() as con:
        con.execute('''
            INSERT INTO pinned_events (event_id, name, date) VALUES (?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET name=excluded.name, date=excluded.date
        ''', (event_id, name, ev_date))
    return Response(
        json.dumps({'id': event_id, 'name': name, 'date': ev_date}),
        status=200, mimetype='application/json'
    )


@app.route('/pinned-runners', methods=['GET', 'POST', 'DELETE'])
def pinned_runners():
    if request.method == 'GET':
        with _db() as con:
            rows = con.execute('SELECT name FROM pinned_runners ORDER BY name').fetchall()
        return Response(json.dumps([r[0] for r in rows]), status=200, mimetype='application/json')

    name = request.args.get('name', '').strip()
    if not name:
        return Response(json.dumps({"error": "Missing name"}), status=400, mimetype='application/json')

    if request.method == 'DELETE':
        with _db() as con:
            con.execute('DELETE FROM pinned_runners WHERE name = ?', (name,))
        return Response('{}', status=200, mimetype='application/json')

    # POST
    with _db() as con:
        con.execute('INSERT OR REPLACE INTO pinned_runners (name) VALUES (?)', (name,))
    return Response(json.dumps({"name": name}), status=200, mimetype='application/json')


@app.route('/livelink', methods=['GET', 'POST'])
def livelink():
    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')
    if request.method == 'GET':
        with _db() as con:
            row = con.execute('SELECT race_id, verified FROM livelinks WHERE event_id = ?', (event_id,)).fetchone()
        if row:
            return Response(json.dumps({"raceId": row[0], "verified": row[1]}), status=200, mimetype='application/json')
        return Response('{"raceId":null}', status=404, mimetype='application/json')
    # POST — save or clear
    race_id = request.args.get('raceId')
    verified = request.args.get('verified', 'unverified')
    with _db() as con:
        if race_id:
            con.execute('''
                INSERT INTO livelinks (event_id, race_id, verified) VALUES (?, ?, ?)
                ON CONFLICT(event_id) DO UPDATE SET race_id = excluded.race_id, verified = excluded.verified
            ''', (event_id, race_id, verified))
        else:
            con.execute('DELETE FROM livelinks WHERE event_id = ?', (event_id,))
    return Response('{}', status=200, mimetype='application/json')


@app.route('/raceinfo')
def raceinfo():
    race_id = request.args.get('raceId')
    if not race_id:
        return Response('{"error":"Missing raceId"}', status=400, mimetype='application/json')
    try:
        if re.fullmatch(r'\d+', race_id):
            data = _liveres_raceinfo(race_id)
            return Response(json.dumps(data), status=200, mimetype='application/json')
        resp = requests.get(f'{TIME4O_BASE}/race/{race_id}', timeout=15)
        return Response(resp.text, status=resp.status_code, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')


@app.route('/refresh', methods=['POST'])
def refresh():
    event_id = request.args.get('eventId')
    with _db() as con:
        con.execute('DELETE FROM cache WHERE key = ?', ('events',))
        if event_id:
            con.execute('DELETE FROM cache WHERE key = ?', (f'startlist:{event_id}',))
            con.execute('DELETE FROM cache WHERE key = ?', (f'entries:{event_id}',))
    return Response('{}', status=200, mimetype='application/json')


@app.route('/liveresults')
def liveresults():
    race_id = request.args.get('raceId')
    if not race_id:
        return Response('{"error":"Missing raceId"}', status=400, mimetype='application/json')
    try:
        if re.fullmatch(r'\d+', race_id):
            entries = _liveres_results(race_id)
            return Response(json.dumps({'data': entries}), status=200, mimetype='application/json')
        resp = requests.get(f'{TIME4O_BASE}/race/{race_id}/entry', timeout=15)
        return Response(resp.text, status=resp.status_code, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')


def _parse_result_time(time_str):
    """Parse Eventor time string (M:SS, MM:SS, or H:MM:SS) to milliseconds."""
    if not time_str:
        return None
    parts = time_str.split(':')
    try:
        if len(parts) == 2:
            return (int(parts[0]) * 60 + int(parts[1])) * 1000
        if len(parts) == 3:
            return (int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])) * 1000
    except ValueError:
        pass
    return None


def _parse_eventor_results(xml_text):
    """Parse Eventor ResultList XML; return entries for tracked persons only."""
    tracked_ids = set(pid.strip() for pid in TRACKED_IDS.split(','))
    entries = []
    for cls_block in re.finditer(r'<ClassResult\b[^>]*>(.*?)</ClassResult>', xml_text, re.DOTALL):
        cls_text = cls_block.group(1)
        cn = re.search(r'<EventClass\b[^>]*>.*?<Name>([^<]+)</Name>', cls_text, re.DOTALL)
        class_name = cn.group(1) if cn else ''
        for pr_block in re.finditer(r'<PersonResult>(.*?)</PersonResult>', cls_text, re.DOTALL):
            pr = pr_block.group(1)
            pid_m = re.search(r'<PersonId>(\d+)</PersonId>', pr)
            if not pid_m or pid_m.group(1) not in tracked_ids:
                continue
            family_m = re.search(r'<Family>([^<]+)</Family>', pr)
            given_m  = re.search(r'<Given[^>]*>([^<]+)</Given>', pr)
            org_m    = re.search(r'<Organisation>.*?<Name>([^<]+)</Name>', pr, re.DOTALL)
            name     = f'{given_m.group(1) if given_m else ""} {family_m.group(1) if family_m else ""}'.strip()
            org      = org_m.group(1) if org_m else ''
            res_m    = re.search(r'<Result>(.*?)</Result>', pr, re.DOTALL)
            if not res_m:
                entries.append({'person': {'name': name, 'club': org}, 'class': class_name,
                                'status': {'status': 'DidNotStart'}, 'time': None, 'position': None, 'start': None})
                continue
            res        = res_m.group(1)
            status_m   = re.search(r'<CompetitorStatus value="([^"]+)"', res)
            time_m     = re.search(r'<Time>([^<]+)</Time>', res)
            timediff_m = re.search(r'<TimeDiff>([^<]+)</TimeDiff>', res)
            pos_m      = re.search(r'<ResultPosition>(\d+)</ResultPosition>', res)
            finish_m   = re.search(r'<FinishTime>.*?<Clock>([^<]+)</Clock>', res, re.DOTALL)
            status     = status_m.group(1) if status_m else 'DidNotStart'
            time_ms    = _parse_result_time(time_m.group(1)) if time_m else None
            finish_hhmm = finish_m.group(1)[:5] if finish_m else None
            time_obj   = None
            if time_ms is not None:
                time_obj = {'time': time_ms}
                if finish_hhmm:
                    time_obj['finishHHMM'] = finish_hhmm
            entries.append({
                'person':   {'name': name, 'club': org},
                'class':    class_name,
                'status':   {'status': status},
                'time':     time_obj,
                'timeDiff': timediff_m.group(1) if timediff_m else None,
                'position': int(pos_m.group(1)) if pos_m else None,
                'start':    None,
            })
    return entries


@app.route('/eventresults')
def event_results():
    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')
    cache_key = f'eventresults:{event_id}'
    cached = _cache_get(cache_key)
    if cached:
        return Response(cached, status=200, mimetype='application/json')
    try:
        resp = eventor_get(f'/results/event?eventId={event_id}')
        if not resp.ok:
            return Response(json.dumps({'data': []}), status=200, mimetype='application/json')
        entries = _parse_eventor_results(resp.text)
        result = json.dumps({'data': entries})
        if entries:
            _cache_set(cache_key, result, ttl=600)
        return Response(result, status=200, mimetype='application/json')
    except Exception as e:
        return Response(json.dumps({"error": str(e)}), status=500, mimetype='application/json')


@app.route('/ratass-members')
def ratass_members_route():
    cached = _cache_get('ratass-members')
    if cached:
        return Response(cached, status=200, mimetype='application/json')
    try:
        resp = requests.get(f'{RATASS_BASE}/api/athletes',
                            params={'ratass': '1', 'limit': '500'}, timeout=10)
        if resp.ok:
            _cache_set('ratass-members', resp.text, ttl=3600)
            return Response(resp.text, status=200, mimetype='application/json')
    except Exception as e:
        app.logger.warning('ratass-members failed: %s', e)
    return Response('{"status":"ok","athletes":[]}', status=200, mimetype='application/json')



if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
