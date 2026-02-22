// Just save the gig #3 overview - everything should be set already
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Check full form state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      title: document.querySelector('textarea')?.value?.substring(0, 70) || '',
      categoryValues: Array.from(document.querySelectorAll('[class*="single-value"]'))
        .filter(el => el.offsetParent !== null).map(el => el.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag-name'))
        .map(el => el.textContent.trim()),
      metadata: Array.from(document.querySelectorAll('[class*="metadata"] input[type="checkbox"]:checked'))
        .map(el => (el.closest('label') || el.parentElement)?.textContent?.trim() || ''),
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100))
    });
  `);
  console.log("Form state:", r);

  // Scroll to and click Save & Continue
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found save button';
    }
    return 'no save button';
  `);
  console.log(r);
  await sleep(1000);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);

    // Wait longer for save to process
    console.log("Waiting for save...");
    await sleep(8000);

    // Check result
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors,
        body: document.body?.innerText?.substring(0, 300)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
