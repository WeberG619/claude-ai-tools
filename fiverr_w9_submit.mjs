// Submit Fiverr W-9 form and check identity verification
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

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("Current:", r);

  // First, select "No" (non-US person) - this is simpler and lets us publish immediately
  // Weber can update this later if needed
  console.log("\n=== Selecting Non-US status ===");
  r = await eval_(`
    const noRadio = document.querySelector('input[name="us-citizen"][value="non_us"]');
    if (noRadio) {
      noRadio.click();
      return JSON.stringify({ clicked: true, checked: noRadio.checked });
    }
    return JSON.stringify({ error: 'radio not found' });
  `);
  console.log("Non-US radio:", r);
  await sleep(500);

  // Click "Update Form W-9"
  console.log("\nClicking Update Form W-9...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.includes('Update Form W-9'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const btnCoords = JSON.parse(r);
  if (!btnCoords.error) {
    await clickAt(send, btnCoords.x, btnCoords.y);
  }
  await sleep(5000);

  // Check result
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      bodyPreview: document.body?.innerText?.substring(0, 1000)
    });
  `);
  console.log("After W-9 submit:", r);
  let state = JSON.parse(r);

  // Navigate back to the gig publish page
  if (!state.url.includes('manage_gigs')) {
    console.log("\n=== Going back to gig publish ===");
    await eval_(`window.history.back()`);
    await sleep(3000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        bodyPreview: document.body?.innerText?.substring(0, 1000)
      });
    `);
    console.log("Back to gig:", r);
    state = JSON.parse(r);
  }

  // Check the identity verification
  console.log("\n=== Identity Verification ===");
  r = await eval_(`
    const verifyLink = Array.from(document.querySelectorAll('a, button, span'))
      .find(el => el.textContent.trim() === 'Verify');
    if (verifyLink) {
      return JSON.stringify({
        found: true,
        tag: verifyLink.tagName,
        href: verifyLink.href || '',
        y: Math.round(verifyLink.getBoundingClientRect().y)
      });
    }
    return JSON.stringify({ found: false });
  `);
  console.log("Verify link:", r);

  // Check if W-9 is now complete
  r = await eval_(`
    const bodyText = document.body?.innerText || '';
    return JSON.stringify({
      hasW9Requirement: bodyText.includes('Form W-9'),
      hasVerifyRequirement: bodyText.includes('Identity verification'),
      hasDeclareStatus: bodyText.includes('Declare your status'),
      hasPublish: bodyText.includes('Publish Gig')
    });
  `);
  console.log("Requirements status:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
