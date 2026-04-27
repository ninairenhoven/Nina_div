import os
import re
import time
import sqlite3
import requests
from datetime import date, timedelta
from flask import Flask, send_from_directory, Response, request
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

API_KEY      = os.getenv('EVENTOR_API_KEY')
BASE_URL    = 'https://eventor.orientering.no/api'
TIME4O_BASE = 'https://center.time4o.com/api/v1'
MY_PERSON_ID  = os.getenv('EVENTOR_PERSON_ID', '45234')
TRACKED_IDS   = os.getenv('EVENTOR_TRACKED_IDS', MY_PERSON_ID)

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
            race_id  TEXT NOT NULL
        )
    ''')
    con.commit()
    return con


def _cache_get(key):
    today = date.today().isoformat()
    now   = time.time()
    with _db() as con:
        row = con.execute(
            'SELECT value, cached_date, expires_at FROM cache WHERE key = ?', (key,)
        ).fetchone()
    if row and row[1] == today and row[2] > now:
        return row[0]
    return None


def _cache_set(key, value, ttl=CACHE_TTL):
    today = date.today().isoformat()
    now   = time.time()
    with _db() as con:
        con.execute('''
            INSERT INTO cache (key, value, cached_date, expires_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value      = excluded.value,
                cached_date = excluded.cached_date,
                expires_at  = excluded.expires_at
        ''', (key, value, today, now + ttl))


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

    return ('<?xml version="1.0" encoding="utf-8"?><StartListList>'
            + ''.join(all_items)
            + '</StartListList>')


def _get_events_xml():
    cached = _cache_get('events')
    if cached:
        app.logger.info('Returning events XML from cache')
        return cached

    app.logger.info('Cache miss — fetching from Eventor')
    xml = _merge_starts_for_all()
    _cache_set('events', xml)
    return xml


# ── Routes ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('cloudflare', 'index.html')


@app.route('/my-events')
def my_events():
    resp = eventor_get(f'/entries?personIds={TRACKED_IDS}&includePersonElement=true')
    if resp.ok:
        return Response(resp.text, status=resp.status_code, mimetype='application/xml')

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
    return Response(resp.text, status=resp.status_code, mimetype='application/xml')


@app.route('/livelink', methods=['GET', 'POST'])
def livelink():
    event_id = request.args.get('eventId')
    if not event_id:
        return Response('{"error":"Missing eventId"}', status=400, mimetype='application/json')
    if request.method == 'GET':
        with _db() as con:
            row = con.execute('SELECT race_id FROM livelinks WHERE event_id = ?', (event_id,)).fetchone()
        if row:
            return Response(f'{{"raceId":"{row[0]}"}}', status=200, mimetype='application/json')
        return Response('{"raceId":null}', status=404, mimetype='application/json')
    # POST — save or clear
    race_id = request.args.get('raceId')
    with _db() as con:
        if race_id:
            con.execute('''
                INSERT INTO livelinks (event_id, race_id) VALUES (?, ?)
                ON CONFLICT(event_id) DO UPDATE SET race_id = excluded.race_id
            ''', (event_id, race_id))
        else:
            con.execute('DELETE FROM livelinks WHERE event_id = ?', (event_id,))
    return Response('{}', status=200, mimetype='application/json')


@app.route('/raceinfo')
def raceinfo():
    race_id = request.args.get('raceId')
    if not race_id:
        return Response('{"error":"Missing raceId"}', status=400, mimetype='application/json')
    try:
        resp = requests.get(f'{TIME4O_BASE}/race/{race_id}', timeout=15)
        return Response(resp.text, status=resp.status_code, mimetype='application/json')
    except Exception as e:
        return Response(f'{{"error":"{e}"}}', status=500, mimetype='application/json')


@app.route('/refresh', methods=['POST'])
def refresh():
    event_id = request.args.get('eventId')
    with _db() as con:
        con.execute('DELETE FROM cache WHERE key = ?', ('events',))
        if event_id:
            con.execute('DELETE FROM cache WHERE key = ?', (f'startlist:{event_id}',))
    return Response('{}', status=200, mimetype='application/json')


@app.route('/liveresults')
def liveresults():
    race_id = request.args.get('raceId')
    if not race_id:
        return Response('{"error":"Missing raceId"}', status=400, mimetype='application/json')
    try:
        resp = requests.get(f'{TIME4O_BASE}/race/{race_id}/entry', timeout=15)
        return Response(resp.text, status=resp.status_code, mimetype='application/json')
    except Exception as e:
        return Response(f'{{"error":"{e}"}}', status=500, mimetype='application/json')


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)
