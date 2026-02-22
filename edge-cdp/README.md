# Edge CDP Browser Automation

Reliable browser automation via Edge's Chrome DevTools Protocol (CDP).

## Setup

Edge must be launched with remote debugging enabled:

```powershell
# Launch Edge with CDP on port 9223 (using default profile with saved sessions)
Start-Process "msedge.exe" -ArgumentList "--remote-debugging-port=9223"
```

## Connection

Edge CDP binds to IPv6 only (`::1`), not IPv4 (`127.0.0.1`).

From Windows Node.js (v22+ for native WebSocket):
```javascript
// List pages
http.get('http://[::1]:9223/json', ...)

// Connect to a page's WebSocket
const ws = new WebSocket(page.webSocketDebuggerUrl);
```

From WSL2: **Cannot connect directly** — must run Node.js scripts on Windows side:
```bash
powershell.exe -Command "& 'C:\Program Files\nodejs\node.exe' '/path/to/script.js'"
```

## Usage Pattern

1. Get page list from `http://[::1]:9223/json`
2. Find target page by URL
3. Connect via WebSocket to `page.webSocketDebuggerUrl`
4. Send CDP commands: `Runtime.evaluate`, `Page.navigate`, etc.

## Supabase Management API

The most reliable way to execute SQL on Supabase is via the Management API:

```javascript
// Extract access token from Supabase dashboard's localStorage
const authData = JSON.parse(localStorage.getItem('supabase.dashboard.auth.token'));
const token = authData.access_token;

// Execute SQL
const r = await fetch('https://api.supabase.com/v1/projects/{ref}/database/query', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({ query: 'SELECT 1' })
});
```

## Key Files

- `edge_helper.js` — Reusable CDP helper module
- `/tmp/edge_exec_sql_mgmt.js` — SQL execution via Management API
- `/tmp/edge_test_final.js` — Auth E2E test suite
