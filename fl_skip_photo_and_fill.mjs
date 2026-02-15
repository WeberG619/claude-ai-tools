// Skip photo step, fill remaining profile fields, try to complete profile
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  let r = await eval_(`return location.href`);
  console.log("Current URL:", r);

  // Close any modal first
  r = await eval_(`
    const closeBtn = document.querySelector('.ModalCloseButton, [class*="ModalClose"]');
    if (closeBtn) { closeBtn.click(); return 'closed modal'; }
    return 'no modal';
  `);
  console.log("Modal:", r);
  await sleep(500);

  // Click Next to skip photo step
  console.log("\nClicking Next to skip photo...");
  r = await eval_(`
    const nextBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
    if (nextBtn) {
      nextBtn.scrollIntoView({ block: 'center' });
      const rect = nextBtn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(3000);
  }

  r = await eval_(`return location.href`);
  console.log("After Next:", r);

  // Check what page we're on now
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      inputs: Array.from(document.querySelectorAll('input, textarea'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden')
        .map(i => ({ tag: i.tagName, type: i.type, id: i.id, name: i.name, placeholder: i.placeholder?.substring(0, 50), value: i.value?.substring(0, 30) })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => b.textContent.trim().substring(0, 40)),
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nPage state:", r);

  const state = JSON.parse(r);

  // Handle each possible page
  if (state.url.includes('headline-and-summary')) {
    console.log("\n=== On headline-and-summary page ===");
    // Use execCommand approach that worked in v3
    const fields = [
      { id: "professional-headline", value: "Writer & Data Specialist" },
      { id: "summary", value: "Professional writer and data specialist. I deliver high-quality content and accurate data processing using AI-enhanced tools for fast, precise results across writing, research, data entry and Excel projects. Meticulous attention to detail with low error rates." },
      { id: "hourly-rate", value: "35" }
    ];

    for (const field of fields) {
      console.log(`\nFilling #${field.id}...`);
      r = await eval_(`
        const el = document.getElementById(${JSON.stringify(field.id)});
        if (!el) return 'NOT FOUND';
        el.focus();
        el.select ? el.select() : document.execCommand('selectAll', false, null);
        document.execCommand('delete', false, null);
        document.execCommand('insertText', false, ${JSON.stringify(field.value)});
        return 'set to: "' + (el.value || '').substring(0, 50) + '..." (' + (el.value || '').length + ' chars)';
      `);
      console.log("  Result:", r);
    }

    await sleep(500);

    // Click Save/Next
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => (b.textContent.trim() === 'Save' || b.textContent.trim() === 'Next') && b.offsetParent !== null);
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ text: btn.textContent.trim(), x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      return null;
    `);

    if (r) {
      const btnData = JSON.parse(r);
      console.log(`\nClicking "${btnData.text}"...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btnData.x, y: btnData.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btnData.x, y: btnData.y, button: "left", clickCount: 1 });
      await sleep(4000);
    }

    // Check result
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error" i], [class*="validation" i]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({ url: location.href, errors, preview: document.body.innerText.substring(0, 1000) });
    `);
    console.log("\nAfter save:", r);

  } else if (state.url.includes('photo-and-name')) {
    // Still on photo page - the name fields might need filling
    console.log("\n=== Still on photo-and-name - filling name fields ===");
    const nameFields = state.inputs.filter(i => !i.value);
    console.log("Empty inputs:", nameFields);

    // Fill first name
    r = await eval_(`
      const fn = document.getElementById('first-name') || document.querySelector('input[placeholder*="First" i]');
      if (fn && !fn.value) {
        fn.focus();
        document.execCommand('insertText', false, 'Weber');
        return 'set first name';
      }
      return fn ? 'already has: ' + fn.value : 'not found';
    `);
    console.log("First name:", r);

    // Fill last name
    r = await eval_(`
      const ln = document.getElementById('last-name') || document.querySelector('input[placeholder*="Last" i]');
      if (ln && !ln.value) {
        ln.focus();
        document.execCommand('insertText', false, 'Gouin');
        return 'set last name';
      }
      return ln ? 'already has: ' + ln.value : 'not found';
    `);
    console.log("Last name:", r);

    await sleep(300);

    // Click Next again
    r = await eval_(`
      const nextBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Next' && b.offsetParent !== null);
      if (nextBtn) {
        const rect = nextBtn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      return null;
    `);
    if (r) {
      const pos = JSON.parse(r);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(3000);
    }

    r = await eval_(`return JSON.stringify({ url: location.href, preview: document.body.innerText.substring(0, 1000) })`);
    console.log("\nAfter Next:", r);
  }

  // Check if we ended up on the dashboard or somewhere new
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      completeProfile: document.body.innerText.includes('Complete your profile'),
      bidSection: document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Bid Amount'),
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== FINAL STATE ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
