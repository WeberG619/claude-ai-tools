// Save W-9 and publish Fiverr gig
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
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Navigate to W-9 page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim()
    });
  `);
  console.log("Current:", r);
  let state = JSON.parse(r);

  // If on publish page, click "Declare your status"
  if (state.step === 'Publish' || state.url.includes('publish')) {
    console.log("On publish page. Clicking Declare your status...");
    await eval_(`
      const link = Array.from(document.querySelectorAll('a, button, span'))
        .find(el => el.textContent.trim() === 'Declare your status');
      if (link) link.click();
    `);
    await sleep(3000);
  }

  // Now on W-9 page
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      hasNoRadio: !!document.querySelector('input[name="us-citizen"][value="non_us"]'),
      noChecked: document.querySelector('input[name="us-citizen"][value="non_us"]')?.checked,
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("W-9 page:", r);

  // Ensure "No" is selected
  await eval_(`
    const radio = document.querySelector('input[name="us-citizen"][value="non_us"]');
    if (radio && !radio.checked) radio.click();
  `);
  await sleep(300);

  // Find and click Save button
  console.log("\n=== Clicking Save ===");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 30),
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        class: (el.className?.toString() || '').substring(0, 60)
      }))
      .filter(b => b.text.length > 0);
    return JSON.stringify(btns);
  `);
  console.log("Buttons:", r);

  const btns = JSON.parse(r);
  const saveBtn = btns.find(b => b.text === 'Save') || btns.find(b => b.text.includes('Update'));
  if (saveBtn) {
    console.log(`Clicking "${saveBtn.text}" at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);
  }

  // Check result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 800)
    });
  `);
  console.log("After save:", r);
  state = JSON.parse(r);

  // If we got redirected or still on W-9, navigate back to publish
  if (state.url.includes('financial-docs') || !state.url.includes('manage_gigs')) {
    console.log("\nNavigating back to gig publish...");
    // Navigate to the gig edit page directly
    await eval_(`
      window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs/do-accurate-data-entry-excel-spreadsheet-work-and-data-processing/edit?wizard=5&tab=publish';
    `);
    await sleep(5000);
  }

  // Check publish page status
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 1000),
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      hasW9: document.body?.innerText?.includes('Form W-9'),
      hasDeclare: document.body?.innerText?.includes('Declare your status'),
      hasVerify: document.body?.innerText?.includes('Identity verification'),
      hasHumanTouch: document.body?.innerText?.includes('human touch')
    });
  `);
  console.log("Publish page:", r);
  state = JSON.parse(r);

  // If no more requirements, click Publish
  if (!state.hasW9 && !state.hasVerify && !state.hasDeclare && state.step === 'Publish') {
    console.log("\n=== All clear! Publishing gig... ===");
    await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Publish') && !b.textContent.includes('Preview'));
      if (btn) btn.click();
    `);
    await sleep(5000);
    r = await eval_(`return JSON.stringify({ url: location.href, bodyPreview: document.body?.innerText?.substring(0, 500) })`);
    console.log("After publish:", r);
  } else if (state.hasHumanTouch) {
    console.log("\nBot detection triggered. Page needs manual refresh.");
  } else {
    console.log("\nStill has requirements to complete:");
    if (state.hasW9 || state.hasDeclare) console.log("  - W-9 declaration");
    if (state.hasVerify) console.log("  - Identity verification");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
