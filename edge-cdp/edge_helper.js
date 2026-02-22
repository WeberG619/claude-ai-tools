// Edge CDP Helper — reusable module for browser automation
// Usage: const { getPages, cdpCommand, getSupabaseToken, runSupabaseQuery } = require('./edge_helper');

const http = require('http');

const CDP_HOST = '[::1]';
const CDP_PORT = 9223;

/**
 * Get list of open pages from Edge CDP
 */
function getPages() {
  return new Promise((resolve, reject) => {
    http.get(`http://${CDP_HOST}:${CDP_PORT}/json`, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(JSON.parse(data)));
    }).on('error', reject);
  });
}

/**
 * Send a CDP command to a page via WebSocket
 */
function cdpCommand(wsUrl, method, params = {}, timeout = 60000) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => ws.send(JSON.stringify({ id: 1, method, params }));
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id === 1) { resolve(msg); ws.close(); }
    };
    ws.onerror = (e) => reject(e);
    setTimeout(() => { try { ws.close(); } catch(e) {} reject(new Error('timeout')); }, timeout);
  });
}

/**
 * Find a page by URL pattern
 */
async function findPage(urlPattern) {
  const pages = await getPages();
  return pages.find(p => p.type === 'page' && p.url.includes(urlPattern));
}

/**
 * Evaluate JavaScript in a page context
 */
async function evaluate(wsUrl, expression, awaitPromise = false) {
  const result = await cdpCommand(wsUrl, 'Runtime.evaluate', {
    expression,
    awaitPromise,
    returnByValue: true
  });
  return result.result?.result?.value;
}

/**
 * Get Supabase access token from dashboard localStorage
 * Requires Edge to be on a supabase.com page
 */
async function getSupabaseToken(wsUrl) {
  const expr = `(() => {
    try {
      const data = JSON.parse(localStorage.getItem('supabase.dashboard.auth.token'));
      return data?.access_token || null;
    } catch(e) { return null; }
  })()`;
  return await evaluate(wsUrl, expr);
}

/**
 * Execute SQL on Supabase via Management API
 * Requires Edge to be on a supabase.com page (for auth token)
 */
async function runSupabaseQuery(wsUrl, projectRef, sql) {
  const expr = `(async()=>{
    try {
      const authData = JSON.parse(localStorage.getItem('supabase.dashboard.auth.token'));
      const token = authData?.access_token;
      if (!token) return JSON.stringify({error: 'No access token'});
      const r = await fetch('https://api.supabase.com/v1/projects/${projectRef}/database/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token },
        body: JSON.stringify({query: ${JSON.stringify(sql)}})
      });
      const text = await r.text();
      return JSON.stringify({status: r.status, body: text});
    } catch(e) { return JSON.stringify({error: e.message}); }
  })()`;
  const raw = await evaluate(wsUrl, expr, true);
  return JSON.parse(raw || '{}');
}

module.exports = { getPages, cdpCommand, findPage, evaluate, getSupabaseToken, runSupabaseQuery };
