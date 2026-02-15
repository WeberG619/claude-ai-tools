// Debug why Save & Continue isn't working on gig #2 overview
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Check current state and any error messages
  let r = await eval_(`
    // Find any error/warning messages on the page
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="warning"], [class*="invalid"], [class*="alert"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => ({
        text: el.textContent.trim().substring(0, 100),
        class: (el.className?.toString() || '').substring(0, 60)
      }));

    // Check all hidden form values
    const hiddenInputs = Array.from(document.querySelectorAll('input[type="hidden"]'))
      .map(el => ({ name: el.name, value: el.value?.substring(0, 60) }));

    // Check the active step/tab
    const activeStep = document.querySelector('.active-step, [class*="active"][class*="step"], .tab-active')?.textContent?.trim() || '';

    // Check tag count text
    const tagCount = document.querySelector('[class*="tag-count"], [class*="tag"][class*="limit"]')?.textContent?.trim() || '';

    return JSON.stringify({ errors, hiddenInputs: hiddenInputs.slice(0, 15), activeStep, tagCount });
  `);
  console.log("Page state:", r);

  // Check if there's a service type dropdown we missed
  r = await eval_(`
    const allDropdowns = Array.from(document.querySelectorAll('.orca-combo-box-container, [class*="select-container"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 60) || '',
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(allDropdowns);
  `);
  console.log("\nAll dropdowns:", r);

  // Check for a service type or metadata section
  r = await eval_(`
    // Look for any unfilled required fields
    const formLabels = Array.from(document.querySelectorAll('label, [class*="label"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y)
      }))
      .filter(l => l.text.length > 0);
    return JSON.stringify(formLabels);
  `);
  console.log("\nForm labels:", r);

  // Check the full visible page content below the fold
  r = await eval_(`
    return document.body?.innerText?.substring(0, 3000) || '';
  `);
  console.log("\nFull page text:", r);

  // Scroll down to check for more fields
  r = await eval_(`
    window.scrollTo(0, document.body.scrollHeight);
    return 'scrolled';
  `);
  await sleep(1000);

  // Check what's visible after scrolling
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        disabled: el.disabled,
        type: el.type || ''
      }))
      .filter(b => b.text.length > 0 && b.y > 0);
    return JSON.stringify(btns);
  `);
  console.log("\nButtons after scroll:", r);

  // Try to click Save & Continue with the correct button
  const btns = JSON.parse(r);
  const saveBtn = btns.find(b => b.text.includes('Save') && b.text.includes('Continue'));
  if (saveBtn) {
    console.log(`\nClicking Save & Continue at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(3000);

    // Check for errors after click
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="warning"], [class*="invalid"], [role="alert"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        errors,
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 1000)
      });
    `);
    console.log("After save attempt:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
