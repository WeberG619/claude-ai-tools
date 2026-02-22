const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
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

(async () => {
  let { ws, send, eval_ } = await connectToPage("dataannotation");

  // Check current form state
  let r = await eval_(`
    const inputs = document.querySelectorAll('input');
    const results = [];
    inputs.forEach(inp => {
      results.push({
        name: inp.name || inp.id || inp.placeholder || 'unknown',
        type: inp.type,
        value: inp.value
      });
    });
    return JSON.stringify(results);
  `);
  console.log("Form fields:", r);

  // Fill first name
  r = await eval_(`
    const inputs = document.querySelectorAll('input');
    for (const inp of inputs) {
      const label = inp.closest('div')?.querySelector('label')?.textContent || '';
      if (label.includes('First Name') || inp.name?.toLowerCase().includes('first')) {
        inp.focus();
        inp.value = '';
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(inp, 'Weber');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        return 'filled first name';
      }
    }
    return 'first name field not found';
  `);
  console.log("First name:", r);

  // Fill last name
  r = await eval_(`
    const inputs = document.querySelectorAll('input');
    for (const inp of inputs) {
      const label = inp.closest('div')?.querySelector('label')?.textContent || '';
      if (label.includes('Last Name') || inp.name?.toLowerCase().includes('last')) {
        inp.focus();
        inp.value = '';
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(inp, 'Gouin');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        return 'filled last name';
      }
    }
    return 'last name field not found';
  `);
  console.log("Last name:", r);

  // Fill phone
  r = await eval_(`
    const inputs = document.querySelectorAll('input');
    for (const inp of inputs) {
      const label = inp.closest('div')?.querySelector('label')?.textContent || '';
      if (label.includes('Phone') || inp.name?.toLowerCase().includes('phone') || inp.type === 'tel') {
        inp.focus();
        inp.value = '';
        const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        nativeInputValueSetter.call(inp, '7865879726');
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
        return 'filled phone';
      }
    }
    return 'phone field not found';
  `);
  console.log("Phone:", r);

  await sleep(500);

  // Check page state after filling
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\nPage after fill:", r);

  // Look for submit button
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, input[type="submit"]'));
    return JSON.stringify(btns.map(b => ({
      text: b.textContent?.trim().substring(0, 50),
      type: b.type,
      disabled: b.disabled
    })));
  `);
  console.log("\nButtons:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
