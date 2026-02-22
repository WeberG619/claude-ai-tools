// Try to modify city in React/app state or via API before submitting
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const msgId = id++;
    pending.set(msgId, { res, rej });
    ws.send(JSON.stringify({ id: msgId, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(() => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Close any open dropdowns
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  await sleep(500);

  // Strategy 1: Find React fiber state and modify city
  let r = await eval_(`
    // Look for React fiber on the element showing "Buffalo"
    const buffaloSpan = Array.from(document.querySelectorAll('span'))
      .find(el => el.textContent.includes('Buffalo'));
    
    if (!buffaloSpan) return JSON.stringify({ error: 'no Buffalo span' });
    
    // Walk up to find React fiber
    let el = buffaloSpan;
    let fiberKey = null;
    for (const key of Object.keys(el)) {
      if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance')) {
        fiberKey = key;
        break;
      }
    }
    
    // Also check parent elements
    let fiber = null;
    let current = buffaloSpan;
    for (let i = 0; i < 15; i++) {
      for (const key of Object.keys(current)) {
        if (key.startsWith('__reactFiber') || key.startsWith('__reactInternalInstance') || key.startsWith('__reactProps')) {
          if (!fiberKey) fiberKey = key;
          const f = current[key];
          if (f && f.memoizedProps) {
            const props = JSON.stringify(f.memoizedProps).substring(0, 200);
            if (props.includes('Buffalo') || props.includes('city') || props.includes('location')) {
              return JSON.stringify({ found: true, level: i, key, props });
            }
          }
          if (f && f.memoizedState) {
            const state = JSON.stringify(f.memoizedState).substring(0, 200);
            if (state.includes('Buffalo') || state.includes('city')) {
              return JSON.stringify({ found: true, level: i, key, state });
            }
          }
        }
      }
      current = current.parentElement;
      if (!current) break;
    }
    
    return JSON.stringify({ fiberKey, checked: 'no match found' });
  `);
  console.log("React state search:", r);

  // Strategy 2: Look for Redux/Zustand/Context store
  r = await eval_(`
    // Check for common state management
    const stores = {};
    if (window.__REDUX_DEVTOOLS_EXTENSION__) stores.redux = true;
    if (window.__STORE__) stores.store = true;
    if (window.__NEXT_DATA__) stores.nextData = JSON.stringify(window.__NEXT_DATA__).substring(0, 300);
    if (window.__INITIAL_STATE__) stores.initialState = JSON.stringify(window.__INITIAL_STATE__).substring(0, 300);
    
    // Check for any global state containing "Buffalo"
    const globals = [];
    for (const key of Object.keys(window)) {
      try {
        const val = JSON.stringify(window[key]);
        if (val && val.includes('Buffalo') && val.length < 5000) {
          globals.push({ key, snippet: val.substring(0, 200) });
        }
      } catch(e) {}
    }
    
    return JSON.stringify({ stores, globals });
  `);
  console.log("\nGlobal state:", r);

  // Strategy 3: Intercept XHR to find the API and submit corrected data
  // First, let's see what network requests happen when we submit
  r = await eval_(`
    // Check for XSRF token and API base
    const xsrf = document.cookie.split(';').find(c => c.trim().startsWith('XSRF-TOKEN='));
    const token = xsrf ? decodeURIComponent(xsrf.split('=')[1]) : null;
    
    // Check for auth tokens in local/session storage
    const authKeys = [];
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key.includes('token') || key.includes('auth') || key.includes('session')) {
        authKeys.push({ key, value: localStorage.getItem(key).substring(0, 50) });
      }
    }
    
    // Look for the visitor token cookie
    const visitorToken = document.cookie.split(';')
      .find(c => c.trim().startsWith('visitor_signup_gql_token='));
    
    return JSON.stringify({ 
      xsrfToken: token ? token.substring(0, 30) + '...' : null,
      authKeys,
      hasVisitorToken: !!visitorToken
    });
  `);
  console.log("\nAuth info:", r);

  // Strategy 4: Try to use fetch to call Upwork's GraphQL API to update location
  r = await eval_(`
    // Try to intercept what happens when we click "Submit profile"
    // First, monkey-patch fetch to log requests
    const origFetch = window.fetch;
    window._interceptedRequests = [];
    window.fetch = function(...args) {
      window._interceptedRequests.push({
        url: typeof args[0] === 'string' ? args[0] : args[0]?.url,
        method: args[1]?.method || 'GET',
        body: args[1]?.body ? (typeof args[1].body === 'string' ? args[1].body.substring(0, 500) : 'non-string') : null
      });
      return origFetch.apply(this, args);
    };
    
    // Also monkey-patch XMLHttpRequest
    const origXHROpen = XMLHttpRequest.prototype.open;
    const origXHRSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function(method, url) {
      this._interceptUrl = url;
      this._interceptMethod = method;
      return origXHROpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function(body) {
      window._interceptedRequests.push({
        url: this._interceptUrl,
        method: this._interceptMethod,
        body: body ? (typeof body === 'string' ? body.substring(0, 500) : 'non-string') : null
      });
      return origXHRSend.apply(this, arguments);
    };
    
    return 'interceptors installed';
  `);
  console.log("\n" + r);

  // Now click Submit profile and see what API calls are made
  console.log("\nClicking Submit profile to capture API call...");
  await clickAt(send, 238, 312);
  await sleep(5000);

  // Check intercepted requests
  r = await eval_(`
    return JSON.stringify(window._interceptedRequests, null, 2);
  `);
  console.log("\nIntercepted requests:", r);

  // Check current page state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodySnippet: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("\nPage after submit:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
