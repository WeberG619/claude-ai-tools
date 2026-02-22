// Set Fiverr availability ON and check inbox message
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Step 1: Find and click "Set your availability"
  console.log("=== Setting Availability ===");
  let r = await eval_(`
    // Look for availability toggle/link
    const avail = Array.from(document.querySelectorAll('a, button, span, div'))
      .filter(el => {
        const text = el.textContent.trim();
        return (text === 'Set your availability' || text.includes('unavailable')) && el.offsetParent !== null;
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 60),
        tag: el.tagName,
        href: el.href || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));

    // Also look for toggles/switches
    const toggles = Array.from(document.querySelectorAll('[class*="toggle"], [class*="switch"], input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent?.trim()?.substring(0, 40) || '',
        tag: el.tagName,
        type: el.type || '',
        checked: el.checked,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        class: (el.className?.toString() || '').substring(0, 60)
      }));

    return JSON.stringify({ avail, toggles });
  `);
  console.log("Availability elements:", r);
  const elems = JSON.parse(r);

  // Click "Set your availability"
  const setAvail = elems.avail.find(a => a.text === 'Set your availability');
  if (setAvail) {
    console.log(`Clicking "Set your availability" at (${setAvail.x}, ${setAvail.y})`);
    await clickAt(send, setAvail.x, setAvail.y);
    await sleep(3000);

    // Check what appeared - modal or page
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 1000),
        modals: Array.from(document.querySelectorAll('[class*="modal"], [role="dialog"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent?.trim()?.substring(0, 200))
      });
    `);
    console.log("After click:", r);

    // Look for toggle or ON switch
    r = await eval_(`
      const toggles = Array.from(document.querySelectorAll('[class*="toggle"], [class*="switch"], input[type="checkbox"], [role="switch"], [class*="Toggle"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 80),
          role: el.getAttribute('role') || '',
          checked: el.checked || el.getAttribute('aria-checked'),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }))
        .filter(b => b.text.length > 0);
      return JSON.stringify({ toggles, btns: btns.slice(0, 10) });
    `);
    console.log("Toggles/buttons:", r);
  }

  // Step 2: Check inbox message
  console.log("\n=== Checking Inbox ===");
  r = await eval_(`
    const inboxLink = document.querySelector('a[href*="inbox"], a[href*="conversations"]');
    if (inboxLink) {
      const rect = inboxLink.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), href: inboxLink.href });
    }
    return JSON.stringify({ error: 'no inbox link' });
  `);
  console.log("Inbox link:", r);
  const inbox = JSON.parse(r);

  // Find the specific message from anna
  r = await eval_(`
    const msgEl = Array.from(document.querySelectorAll('a, div'))
      .find(el => el.textContent?.includes('anna_39610ogm'));
    if (msgEl) {
      const rect = msgEl.getBoundingClientRect();
      return JSON.stringify({
        text: msgEl.textContent?.trim()?.substring(0, 100),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        tag: msgEl.tagName,
        href: msgEl.href || ''
      });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Anna message:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
