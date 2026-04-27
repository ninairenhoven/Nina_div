/**
 * Eventor Startliste – Cloudflare Worker
 * Proxies two Eventor API endpoints, keeping the API key server-side.
 *
 * Routes:
 *   GET /my-events          → Eventor /entries (falls back to /starts/person)
 *   GET /startlist?eventId= → Eventor /starts/event
 *
 * Secrets (set via: wrangler secret put <NAME>):
 *   EVENTOR_API_KEY
 *   EVENTOR_PERSON_ID
 */

const EVENTOR_BASE = 'https://eventor.orientering.no/api';

// Person IDs for all tracked family members
const TRACKED_IDS = '1620,1621,4427,44761,45124,45234';

const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type',
};

export default {
  async fetch(request, env) {
    if (request.method === 'OPTIONS') {
      return new Response(null, { headers: CORS });
    }

    const { pathname, searchParams } = new URL(request.url);

    try {
      if (pathname === '/my-events') {
        return await myEvents(env);
      }
      if (pathname === '/startlist') {
        const eventId = searchParams.get('eventId');
        if (!eventId) return err('Missing eventId', 400);
        return await startList(eventId, env);
      }
      if (pathname === '/liveresults') {
        const raceId = searchParams.get('raceId');
        if (!raceId) return err('Missing raceId', 400);
        return await liveResultsByRaceId(raceId);
      }
    } catch (e) {
      return err(e.message, 500);
    }

    return err('Not found', 404);
  },
};

async function eventor(path, env) {
  return fetch(`${EVENTOR_BASE}${path}`, {
    headers: { ApiKey: env.EVENTOR_API_KEY },
  });
}

async function myEvents(env) {
  const today = new Date();
  const pad = n => String(n).padStart(2, '0');
  const isoDate = d => `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}`;
  const fromDate = isoDate(new Date(today - 60 * 86400000));
  const toDate   = isoDate(new Date(today + 7 * 86400000));

  // /entries returns 400 with this API key; fetch starts/person for each tracked person instead
  const fetches = TRACKED_IDS.split(',').map(pid =>
    eventor(`/starts/person?personId=${pid.trim()}&fromDate=${fromDate}&toDate=${toDate}`, env).then(r => r.ok ? r.text() : '')
  );
  const bodies = await Promise.all(fetches);

  const items = bodies.flatMap(body => {
    const matches = body.match(/<StartList\b[^>]*>[\s\S]*?<\/StartList>/g);
    return matches || [];
  });

  const merged = `<?xml version="1.0" encoding="utf-8"?><StartListList>${items.join('')}</StartListList>`;
  return xml(merged);
}

async function startList(eventId, env) {
  const resp = await eventor(`/starts/event?eventId=${eventId}`, env);
  return xml(await resp.text(), resp.status);
}

async function liveResultsByRaceId(raceId) {
  const resp = await fetch(`https://center.time4o.com/api/v1/race/${raceId}/entry`);
  return new Response(await resp.text(), {
    status: resp.status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}

function xml(body, status = 200) {
  return new Response(body, {
    status,
    headers: { ...CORS, 'Content-Type': 'application/xml; charset=utf-8' },
  });
}

function err(message, status) {
  return new Response(JSON.stringify({ error: message }), {
    status,
    headers: { ...CORS, 'Content-Type': 'application/json' },
  });
}
