// Try to edit location from submit page - look for profile settings or sidebar nav
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

  // Check for any clickable element near "Buffalo, ID" - links, spans, etc.
  let r = await eval_(`
    // Find all clickable/interactive elements
    const buffaloSpan = Array.from(document.querySelectorAll('span'))
      .find(el => el.textContent.includes('Buffalo'));
    
    if (!buffaloSpan) return JSON.stringify({ error: 'no Buffalo span' });
    
    // Get all parent elements and siblings
    let el = buffaloSpan;
    const info = [];
    for (let i = 0; i < 8; i++) {
      el = el.parentElement;
      if (!el) break;
      const rect = el.getBoundingClientRect();
      const buttons = el.querySelectorAll('button, a, [role="button"]');
      info.push({
        level: i,
        tag: el.tagName,
        class: (el.className || '').substring(0, 60),
        hasButtons: buttons.length,
        buttonTexts: Array.from(buttons).map(b => (b.textContent.trim() || b.getAttribute('aria-label') || '').substring(0, 30)),
        rect: { x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height) }
      });
    }
    
    return JSON.stringify(info, null, 2);
  `);
  console.log("Buffalo parent hierarchy:", r);

  // Also check - can we directly find a "Preview Profile" or navigation link?
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        href: el.href
      }));
    return JSON.stringify(links, null, 2);
  `);
  console.log("\nAll links:", r);

  // Check if "Preview Profile" opens something
  r = await eval_(`
    const previewLink = Array.from(document.querySelectorAll('a, button'))
      .find(el => el.textContent.includes('Preview Profile') && el.offsetParent !== null);
    if (previewLink) {
      const rect = previewLink.getBoundingClientRect();
      return JSON.stringify({
        tag: previewLink.tagName,
        text: previewLink.textContent.trim(),
        href: previewLink.href || '',
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2)
      });
    }
    return JSON.stringify({ error: 'no preview link' });
  `);
  console.log("\nPreview Profile:", r);

  // Try: look at the left sidebar area - there's usually a progress bar/stepper
  r = await eval_(`
    // Check for navigation steps (the 1-10 step indicators)
    const stepElements = Array.from(document.querySelectorAll('[class*="step"], [class*="nav"], [class*="progress"], [class*="sidebar"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className || '').substring(0, 60),
        text: el.textContent.trim().substring(0, 80),
        children: el.children.length
      }));
    return JSON.stringify(stepElements.slice(0, 10), null, 2);
  `);
  console.log("\nStep/nav elements:", r);

  // Check if there's a "Back" or "Edit location" anywhere in the full DOM
  r = await eval_(`
    const allText = document.body.innerHTML;
    const matches = [];
    // Look for location-related edit links
    const patterns = ['edit-location', 'location/edit', 'edit_location', 'editLocation'];
    for (const p of patterns) {
      if (allText.includes(p)) matches.push(p);
    }
    // Also check for any href with "location"
    const locLinks = Array.from(document.querySelectorAll('a[href*="location"]'))
      .map(a => ({ text: a.textContent.trim().substring(0, 30), href: a.href }));
    return JSON.stringify({ patterns: matches, locLinks });
  `);
  console.log("\nLocation-related elements:", r);

  // Last resort: try to directly modify the location through XHR/API
  // First, let's see if we can find what API Upwork uses for the profile
  r = await eval_(`
    // Check if there's a Next.js or React state we can modify
    const reactRoot = document.getElementById('__next') || document.getElementById('root');
    const hasNext = !!document.getElementById('__next');
    const hasReactFiber = !!reactRoot?._reactRootContainer;
    
    // Check cookies for session info
    const cookies = document.cookie.split(';').map(c => c.trim().split('=')[0]);
    
    return JSON.stringify({ hasNext, hasReactFiber, cookieNames: cookies });
  `);
  console.log("\nApp info:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
