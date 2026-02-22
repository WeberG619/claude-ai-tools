// Upwork profile step 10/10: Photo + Location + Submit
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

  // Get full page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      body: document.body.innerText.substring(0, 1500)
    });
  `);
  const page = JSON.parse(r);
  console.log("Page:", page.body.substring(0, 400));

  // Get all form elements
  r = await eval_(`
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="file"]), textarea, select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName, type: el.type, id: el.id || '', name: el.name || '',
        value: el.value.substring(0, 50),
        placeholder: (el.placeholder || '').substring(0, 50),
        label: (el.labels && el.labels[0]) ? el.labels[0].textContent.trim().substring(0, 50) : '',
        disabled: el.disabled,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50
        && !el.textContent.trim().includes('Skip to content'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify({ inputs, btns });
  `);
  const elements = JSON.parse(r);
  console.log("Inputs:", JSON.stringify(elements.inputs));
  console.log("Buttons:", elements.btns.map(b => b.text).join(' | '));

  // Check if location/address fields need filling
  const cityInput = elements.inputs.find(i =>
    i.placeholder.toLowerCase().includes('city') || i.label.toLowerCase().includes('city') ||
    i.placeholder.toLowerCase().includes('address') || i.name.toLowerCase().includes('city')
  );

  // Check if there's a country/state dropdown needing attention
  r = await eval_(`
    const selects = Array.from(document.querySelectorAll('select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        id: el.id, name: el.name || '',
        value: el.value,
        options: Array.from(el.options).slice(0, 5).map(o => o.text),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(selects);
  `);
  console.log("Selects:", r);

  // Check if country is already set (from signup)
  r = await eval_(`
    const countryEl = document.querySelector('[data-test="country"], [class*="country"]');
    const stateEl = document.querySelector('[data-test="state"], [class*="state"]');
    return JSON.stringify({
      country: countryEl ? countryEl.textContent.trim().substring(0, 30) : 'none',
      state: stateEl ? stateEl.textContent.trim().substring(0, 30) : 'none'
    });
  `);
  console.log("Location preset:", r);

  // Look for all text inputs that might need filling
  for (const input of elements.inputs) {
    if (input.disabled) continue;
    if (!input.value && input.type !== 'checkbox' && input.type !== 'radio' && input.type !== 'file') {
      console.log(`Empty input: type=${input.type}, placeholder="${input.placeholder}", label="${input.label}"`);

      // Handle city/address
      if (input.placeholder.toLowerCase().includes('city') || input.label.toLowerCase().includes('city') ||
          input.placeholder.toLowerCase().includes('address') || input.type === 'text') {
        await eval_(`
          const inputs = Array.from(document.querySelectorAll('input[type="text"]:not([disabled])'))
            .filter(el => el.offsetParent !== null && !el.value);
          if (inputs.length > 0) {
            inputs[0].scrollIntoView({ block: 'center' });
            inputs[0].focus();
          }
        `);
        await sleep(300);

        r = await eval_(`
          const inp = document.activeElement;
          if (inp && inp.tagName === 'INPUT') {
            const rect = inp.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'no focus' });
        `);
        const pos = JSON.parse(r);
        if (!pos.error) {
          await clickAt(send, pos.x, pos.y);
          await sleep(200);
          await send("Input.insertText", { text: "Los Angeles" });
          await sleep(2000);

          // Check for autocomplete suggestions
          r = await eval_(`
            const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li, [class*="dropdown"] li, [class*="autocomplete"] li'))
              .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
              .map(el => ({
                text: el.textContent.trim().substring(0, 50),
                x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
                y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
              }));
            return JSON.stringify(opts);
          `);
          console.log("Autocomplete options:", r);
          const opts = JSON.parse(r);
          if (opts.length > 0) {
            const la = opts.find(o => o.text.includes('Los Angeles')) || opts[0];
            await clickAt(send, la.x, la.y);
            console.log(`Selected: ${la.text}`);
          }
          await sleep(500);
        }
        break; // Only fill one input
      }
    }
  }

  // Now try to submit/advance
  await sleep(1000);

  // Find Review/Submit/Next button
  const submitBtn = elements.btns.find(b =>
    b.text.includes('Review') || b.text.includes('Submit') || b.text.includes('Next') || b.text.includes('publish')
  );

  if (submitBtn) {
    // Scroll to button
    await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('${submitBtn.text.substring(0, 15)}'));
      if (btn) btn.scrollIntoView({ block: 'center' });
    `);
    await sleep(300);

    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Review') || b.textContent.trim().includes('Submit'));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent.trim().substring(0, 40) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    const btn = JSON.parse(r);
    if (!btn.error) {
      await clickAt(send, btn.x, btn.y);
      console.log(`Clicked: ${btn.text}`);
      await sleep(5000);

      ws.close(); await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("upwork.com"));

      r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 500) })`);
      const nextPage = JSON.parse(r);
      console.log("\nNext page:", nextPage.step);
      console.log("Body:", nextPage.body.substring(0, 300));

      // If on review page, look for final Submit
      if (nextPage.step === 'review' || nextPage.body.includes('review') || nextPage.body.includes('looks great')) {
        r = await eval_(`
          const btn = Array.from(document.querySelectorAll('button'))
            .find(b => (b.textContent.trim().includes('Submit') || b.textContent.trim().includes('Publish') || b.textContent.trim().includes('Done'))
              && b.offsetParent !== null && !b.textContent.includes('Skip to'));
          if (btn) {
            btn.scrollIntoView({ block: 'center' });
            const rect = btn.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: btn.textContent.trim().substring(0, 40) });
          }
          return JSON.stringify({ error: 'none' });
        `);
        await sleep(300);
        const finalBtn = JSON.parse(r);
        if (!finalBtn.error) {
          await clickAt(send, finalBtn.x, finalBtn.y);
          console.log(`Final click: ${finalBtn.text}`);
          await sleep(5000);
          ws.close(); await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 400) })`);
          console.log("\nFinal page:", r);
        }
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
