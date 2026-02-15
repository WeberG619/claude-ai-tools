// Submit Upwork signup form
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

  // Verify form data
  let r = await eval_(`
    const data = {};
    data.firstName = document.getElementById('first-name-input')?.value || '';
    data.lastName = document.getElementById('last-name-input')?.value || '';
    data.email = document.getElementById('redesigned-input-email')?.value || '';
    data.password = document.getElementById('password-input')?.value ? 'SET' : 'EMPTY';
    data.country = document.querySelector('#country-dropdown .air3-dropdown-toggle-label')?.textContent?.trim() || '';
    const cbs = Array.from(document.querySelectorAll('input[type="checkbox"]'));
    data.checkboxes = cbs.map(cb => ({ checked: cb.checked }));
    return JSON.stringify(data);
  `);
  console.log("Form data:", r);

  // Click "Create my account"
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Create my account'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Submit button:", r);
  const btn = JSON.parse(r);

  if (!btn.error) {
    await sleep(500);
    console.log(`Clicking submit at (${btn.x}, ${btn.y})`);
    await clickAt(send, btn.x, btn.y);
    await sleep(10000);

    // Check result
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        title: document.title,
        body: document.body.innerText.substring(0, 600)
      });
    `);
    console.log("\nAfter submit:", r);

    // Check for errors
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="alert"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify(errors);
    `);
    console.log("Errors:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
