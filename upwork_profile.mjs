// Fill Upwork profile creation
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

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("Current page:", r);

  // Click "Get started"
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, a'))
      .find(el => el.textContent.trim().includes('Get started'));
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Get started:", r);
  const startBtn = JSON.parse(r);

  if (!startBtn.error) {
    await clickAt(send, startBtn.x, startBtn.y);
    await sleep(5000);

    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: document.body.innerText.substring(0, 800)
      });
    `);
    console.log("\nNext page:", r);
  }

  // Explore the current page structure
  r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input, textarea, select, [role="combobox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        id: el.id || '',
        name: el.name || '',
        placeholder: el.placeholder || '',
        label: el.labels?.[0]?.textContent?.trim()?.substring(0, 40) || '',
        ariaLabel: el.getAttribute('aria-label') || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(allInputs);
  `);
  console.log("\nForm elements:", r);

  // Find buttons
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, [role="button"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 40)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(btns);
  `);
  console.log("\nButtons:", r);

  // Find radio buttons / options
  r = await eval_(`
    const radios = Array.from(document.querySelectorAll('input[type="radio"], [role="radio"], [role="option"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        type: el.type,
        name: el.name,
        value: el.value,
        checked: el.checked,
        label: el.labels?.[0]?.textContent?.trim()?.substring(0, 40) || el.closest('label')?.textContent?.trim()?.substring(0, 40) || '',
        x: Math.round(el.getBoundingClientRect().x + 10),
        y: Math.round(el.getBoundingClientRect().y + 10)
      }));
    return JSON.stringify(radios);
  `);
  console.log("\nRadios/options:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
