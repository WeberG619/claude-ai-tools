// Debug why location page won't advance
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

  // Full body text
  let r = await eval_(`return document.body.innerText`);
  console.log("FULL BODY TEXT:");
  console.log(r);
  console.log("\n---\n");

  // All inputs with their state
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input, select, textarea'))
      .filter(el => el.offsetParent !== null || el.type === 'hidden')
      .map(el => ({
        tag: el.tagName, type: el.type, name: el.name || '',
        id: el.id || '', value: el.value,
        placeholder: el.placeholder || '',
        required: el.required,
        valid: el.validity ? el.validity.valid : null,
        validMsg: el.validationMessage || '',
        disabled: el.disabled,
        visible: el.offsetParent !== null
      }));
    return JSON.stringify(inputs, null, 2);
  `);
  console.log("ALL INPUTS:");
  console.log(r);

  // Check for phone country code
  r = await eval_(`
    const phoneSection = document.querySelector('[class*="phone"], [data-test*="phone"]');
    const selects = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name, value: el.value,
        options: Array.from(el.options).slice(0, 3).map(o => o.text + ':' + o.value)
      }));
    // Check for dropdown/combobox for country code
    const combos = Array.from(document.querySelectorAll('[role="combobox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 50),
        class: (el.className || '').substring(0, 50)
      }));
    return JSON.stringify({ phoneSection: phoneSection ? phoneSection.outerHTML.substring(0, 500) : 'none', selects, combos });
  `);
  console.log("\nPhone/Select details:", r);

  // Try scrolling Review button into view and clicking with CDP
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review your profile'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({
        text: btn.textContent.trim(),
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        disabled: btn.disabled,
        ariaDisabled: btn.getAttribute('aria-disabled'),
        class: btn.className.substring(0, 80)
      });
    }
    return JSON.stringify({ error: 'no review btn' });
  `);
  console.log("\nReview button details:", r);
  const reviewBtn = JSON.parse(r);

  if (!reviewBtn.error && !reviewBtn.disabled) {
    await sleep(500);
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked at", reviewBtn.x, reviewBtn.y);
    await sleep(3000);

    // Check for any new errors that appeared
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"], [aria-invalid="true"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 100),
          class: (el.className || '').substring(0, 50),
          tag: el.tagName
        }));
      const url = location.href;
      return JSON.stringify({ errors, url, step: url.split('/').pop().split('?')[0] });
    `);
    console.log("\nAfter click:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
