// Toggle availability ON, close modal, then check inbox
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

  // Close the modal first
  console.log("=== Closing modal ===");
  let r = await eval_(`
    const cancelBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Cancel');
    if (cancelBtn) {
      cancelBtn.click();
      return 'closed modal';
    }
    // Try clicking outside modal
    const overlay = document.querySelector('[class*="overlay"], [class*="backdrop"]');
    if (overlay) {
      overlay.click();
      return 'clicked overlay';
    }
    return 'no modal found';
  `);
  console.log(r);
  await sleep(1000);

  // Now find the availability toggle
  console.log("\n=== Finding availability toggle ===");
  r = await eval_(`
    // Look for the availability section
    const section = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent?.trim()?.startsWith('Availability') && el.children.length > 0 && el.getBoundingClientRect().height < 200);

    // Look for switches/toggles near the availability text
    const switches = Array.from(document.querySelectorAll('[role="switch"], input[type="checkbox"], [class*="toggle"], [class*="switch"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        role: el.getAttribute('role') || '',
        checked: el.checked ?? el.getAttribute('aria-checked'),
        class: (el.className?.toString() || '').substring(0, 80),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width),
        h: Math.round(el.getBoundingClientRect().height)
      }));

    // Check page text around availability
    const availText = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('unavailable') && el.children.length === 0 && el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 80),
        y: Math.round(el.getBoundingClientRect().y)
      }));

    return JSON.stringify({ switches, availText });
  `);
  console.log("Switches:", r);
  const data = JSON.parse(r);

  // Click the switch to toggle availability
  if (data.switches.length > 0) {
    const sw = data.switches[0];
    console.log(`\nClicking switch at (${sw.x}, ${sw.y}) - currently checked: ${sw.checked}`);
    await clickAt(send, sw.x, sw.y);
    await sleep(2000);

    // Check result
    r = await eval_(`
      const sw = document.querySelector('[role="switch"]');
      const bodyText = document.body?.innerText || '';
      return JSON.stringify({
        switchChecked: sw?.getAttribute('aria-checked') || sw?.checked,
        stillUnavailable: bodyText.includes('While unavailable'),
        availSection: bodyText.substring(bodyText.indexOf('Availability'), bodyText.indexOf('Availability') + 200)
      });
    `);
    console.log("After toggle:", r);
  }

  // Step 2: Navigate to inbox to read the message
  console.log("\n=== Navigating to Inbox ===");
  r = await eval_(`
    const viewAll = Array.from(document.querySelectorAll('a'))
      .find(a => a.textContent.trim() === 'View All' && a.href?.includes('inbox'));
    if (viewAll) {
      const rect = viewAll.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    // Try the anna message directly
    const anna = Array.from(document.querySelectorAll('a, div[class]'))
      .find(el => el.textContent?.includes('anna_39610') && el.getBoundingClientRect().width > 50);
    if (anna) {
      const rect = anna.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), isAnna: true });
    }
    return JSON.stringify({ error: 'no inbox link' });
  `);
  console.log("Inbox/Anna:", r);
  const inboxTarget = JSON.parse(r);

  if (!inboxTarget.error) {
    await clickAt(send, inboxTarget.x, inboxTarget.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 3000)
      });
    `);
    const inbox = JSON.parse(r);
    console.log("\nURL:", inbox.url);
    console.log("Inbox:", inbox.body);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
