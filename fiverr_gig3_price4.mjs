// Fill package descriptions and save pricing
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

  // Scroll to top
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Get all textareas
  let r = await eval_(`
    const textareas = Array.from(document.querySelectorAll('textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        value: el.value?.substring(0, 50),
        placeholder: el.placeholder?.substring(0, 40),
        maxLength: el.maxLength,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(textareas);
  `);
  console.log("Textareas:", r);
  const textareas = JSON.parse(r);

  // The description textareas (placeholder "Describe the details...")
  const descTextareas = textareas.filter(t => t.placeholder?.includes('Describe'));
  const nameTextareas = textareas.filter(t => t.placeholder?.includes('Name'));
  console.log(`Name textareas: ${nameTextareas.length}, Description textareas: ${descTextareas.length}`);

  // Fill names if empty
  const names = ["Basic", "Standard", "Premium"];
  for (let i = 0; i < Math.min(nameTextareas.length, 3); i++) {
    if (!nameTextareas[i].value) {
      await tripleClick(send, nameTextareas[i].x, nameTextareas[i].y);
      await sleep(100);
      await send("Input.insertText", { text: names[i] });
      await sleep(200);
      console.log(`Name ${i+1}: "${names[i]}"`);
    } else {
      console.log(`Name ${i+1}: already set "${nameTextareas[i].value}"`);
    }
  }

  // Fill descriptions
  const descs = [
    "Professional resume in clean format with keyword optimization",
    "Resume plus tailored cover letter for your target job role",
    "Full package: resume, cover letter, and LinkedIn optimization"
  ];
  for (let i = 0; i < Math.min(descTextareas.length, 3); i++) {
    await tripleClick(send, descTextareas[i].x, descTextareas[i].y);
    await sleep(100);
    // Select all and replace
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 }); // Ctrl+A
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.insertText", { text: descs[i] });
    await sleep(200);
    console.log(`Desc ${i+1}: "${descs[i]}"`);
  }

  // Verify the full pricing state
  await sleep(500);
  r = await eval_(`
    const textareas = Array.from(document.querySelectorAll('textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value?.substring(0, 60));
    const prices = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value);
    return JSON.stringify({ textareas, prices });
  `);
  console.log("Verified:", r);

  // Also check: is the "Offer packages" toggle ON?
  r = await eval_(`
    const toggler = document.querySelector('.pkgs-toggler');
    if (toggler) return JSON.stringify({ checked: toggler.checked });
    return JSON.stringify({ error: 'no toggler' });
  `);
  console.log("Package toggle:", r);
  const toggle = JSON.parse(r);
  if (toggle.checked === false) {
    console.log("Enabling packages toggle...");
    r = await eval_(`
      const toggler = document.querySelector('.pkgs-toggler');
      const rect = toggler.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + 10) });
    `);
    const togglePos = JSON.parse(r);
    await clickAt(send, togglePos.x, togglePos.y);
    await sleep(500);
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
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
    await sleep(10000);

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
