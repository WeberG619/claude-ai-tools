// Bid on one Freelancer job at a time
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

const JOB_URL = process.argv[2];
const BID_AMOUNT = process.argv[3];
const BID_DAYS = process.argv[4];
const PROPOSAL = process.argv[5];

if (!JOB_URL || !BID_AMOUNT || !BID_DAYS || !PROPOSAL) {
  console.error("Usage: node freelancer_bid_one.mjs <url> <amount> <days> <proposal>");
  process.exit(1);
}

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

async function fillField(send, eval_, selector, value) {
  await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    if (el) { el.focus(); el.select(); }
  `);
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA" });
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
  await sleep(100);
  await send("Input.insertText", { text: value });
  await sleep(200);
  await eval_(`document.querySelector(${JSON.stringify(selector)})?.blur()`);
  await sleep(100);
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected");

  // Navigate to job
  await eval_(`window.location.href = ${JSON.stringify(JOB_URL)}; return 'ok';`);
  await sleep(6000);

  // Check page
  let r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('h1')?.textContent?.trim() || '',
      alreadyBid: (document.body?.innerText || '').includes('Your Bid') || (document.body?.innerText || '').includes('You have already bid'),
      hasBidForm: !!document.querySelector('#bidAmountInput')
    });
  `);
  const state = JSON.parse(r);
  console.log(`Title: ${state.title}`);
  console.log(`Already bid: ${state.alreadyBid}`);
  console.log(`Has form: ${state.hasBidForm}`);

  if (state.alreadyBid) {
    console.log("Already bid on this job - skipping");
    ws.close();
    return;
  }

  if (!state.hasBidForm) {
    console.log("No bid form found");
    ws.close();
    return;
  }

  // Scroll to form
  await eval_(`document.querySelector('#bidAmountInput')?.scrollIntoView({ block: 'center' })`);
  await sleep(500);

  // Fill amount
  console.log(`Setting amount: $${BID_AMOUNT}`);
  await fillField(send, eval_, '#bidAmountInput', BID_AMOUNT);

  // Fill days
  console.log(`Setting days: ${BID_DAYS}`);
  await fillField(send, eval_, '#periodInput', BID_DAYS);

  // Fill proposal
  console.log("Setting proposal...");
  await fillField(send, eval_, '#descriptionTextArea', PROPOSAL);

  // Fill milestone description
  const milestoneSelector = 'input[placeholder*="milestone"]';
  await eval_(`document.querySelector(${JSON.stringify(milestoneSelector)})?.focus()`);
  await sleep(200);
  await send("Input.insertText", { text: "Complete project delivery" });
  await sleep(300);

  // Verify
  r = await eval_(`
    return JSON.stringify({
      amount: document.querySelector('#bidAmountInput')?.value,
      days: document.querySelector('#periodInput')?.value,
      descLen: document.querySelector('#descriptionTextArea')?.value?.length,
      descPreview: document.querySelector('#descriptionTextArea')?.value?.substring(0, 80)
    });
  `);
  console.log("Verification:", r);

  const v = JSON.parse(r);
  if (v.descLen < 100) {
    console.log("ERROR: Proposal too short, aborting");
    ws.close();
    return;
  }

  // Submit
  console.log("Clicking Place Bid...");
  await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Place Bid' && b.offsetParent !== null);
    if (btn) btn.click();
  `);
  await sleep(5000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      success: (document.body?.innerText || '').includes('bidCreated') || location.href.includes('bidCreated') || (document.body?.innerText || '').includes('Your Bid'),
      errors: Array.from(document.querySelectorAll('[class*="error" i], [role="alert"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3)
    });
  `);
  console.log("Result:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
