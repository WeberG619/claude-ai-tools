// Fill gig #3 pricing step (wizard=1) - Resume Writing
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

async function tripleClick(send, x, y) {
  for (let c = 1; c <= 3; c++) {
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: c });
    await sleep(30);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: c });
    await sleep(30);
  }
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Verify we're on pricing
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard')
    });
  `);
  console.log("State:", r);

  // Explore the pricing page structure
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"])'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        type: el.type, name: el.name, id: el.id,
        value: el.value,
        placeholder: el.placeholder,
        class: (el.className || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(inputs);
  `);
  console.log("Inputs:", r);
  const inputs = JSON.parse(r);

  // Get dropdowns/selects
  r = await eval_(`
    const selects = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        name: el.name, id: el.id,
        value: el.value,
        options: Array.from(el.options).map(o => o.text).slice(0, 5).join(', '),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(selects);
  `);
  console.log("Selects:", r);

  // Get page text to understand the layout
  r = await eval_(`
    return document.body.innerText.substring(0, 2000);
  `);
  console.log("Page text:\n", r.substring(0, 1500));

  // Look for price inputs specifically
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('input'))
      .filter(el => {
        const name = (el.name || '').toLowerCase();
        const cls = (el.className || '').toLowerCase();
        return (name.includes('price') || cls.includes('price') || el.type === 'number')
          && el.offsetParent !== null;
      })
      .map(el => ({
        name: el.name, value: el.value, type: el.type,
        class: (el.className || '').substring(0, 50),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(priceInputs);
  `);
  console.log("Price inputs:", r);

  // Look for the penta-select dropdowns used in pricing
  r = await eval_(`
    const pentaSelects = Array.from(document.querySelectorAll('.select-penta-design, [class*="penta"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        class: (el.className || '').substring(0, 50),
        text: el.textContent.trim().substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(pentaSelects);
  `);
  console.log("Penta selects:", r);

  // Scroll down to see if there are more elements
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(500);

  r = await eval_(`
    const allInputs = Array.from(document.querySelectorAll('input:not([type="hidden"]), select, .select-penta-design'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        type: el.type || '',
        name: el.name || '',
        value: el.value || '',
        class: (el.className || '').substring(0, 50),
        text: el.textContent?.trim()?.substring(0, 20) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(allInputs);
  `);
  console.log("All form elements after scroll:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
