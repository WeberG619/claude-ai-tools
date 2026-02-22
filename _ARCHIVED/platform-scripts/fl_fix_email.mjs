// Fix Freelancer.com email - go back and correct it
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

const CORRECT_EMAIL = process.argv[2];
const PASS = process.argv[3];

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com/signup");
  console.log("Connected to Freelancer signup\n");

  // Click back button
  console.log("Step 1: Click back...");
  let r = await eval_(`
    // Find back button/arrow
    const back = document.querySelector('a[href*="back"], button[class*="back"], [class*="Back"]');
    if (back) { back.click(); return 'clicked back button'; }
    // Try the arrow/chevron at top
    const arrows = Array.from(document.querySelectorAll('*')).filter(el => {
      const text = el.textContent.trim();
      return (text === '<' || text === '←' || text === '‹') && el.offsetParent !== null;
    });
    if (arrows.length > 0) { arrows[0].click(); return 'clicked arrow'; }
    // Try browser back
    history.back();
    return 'used history.back()';
  `);
  console.log("  ", r);
  await sleep(3000);

  // Check if we're back on the form
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      hasEmailInput: !!document.querySelector('input[type="email"], input[placeholder="Email"]'),
      preview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("  State:", r);

  const state = JSON.parse(r);

  if (state.hasEmailInput) {
    // Fix the email
    console.log("\nStep 2: Fix email...");
    r = await eval_(`
      const emailInput = document.querySelector('input[type="email"]') || document.querySelector('input[placeholder="Email"]');
      if (!emailInput) return 'email input not found';
      emailInput.focus();
      emailInput.value = '';
      emailInput.dispatchEvent(new Event('input', { bubbles: true }));

      const email = ${JSON.stringify(CORRECT_EMAIL)};
      for (let i = 0; i < email.length; i++) {
        emailInput.value = email.substring(0, i + 1);
        emailInput.dispatchEvent(new Event('input', { bubbles: true }));
      }
      emailInput.dispatchEvent(new Event('change', { bubbles: true }));
      emailInput.dispatchEvent(new Event('blur', { bubbles: true }));
      return 'email set to: ' + emailInput.value;
    `);
    console.log("  ", r);
    await sleep(500);

    // Also re-fill password if needed
    r = await eval_(`
      const passInput = document.querySelector('input[type="password"]');
      if (!passInput || passInput.value.length > 0) return 'password already set or not found';
      passInput.focus();
      const pass = ${JSON.stringify(PASS)};
      passInput.value = pass;
      passInput.dispatchEvent(new Event('input', { bubbles: true }));
      passInput.dispatchEvent(new Event('change', { bubbles: true }));
      return 'password re-entered';
    `);
    console.log("  Password:", r);

    // Check TOS
    r = await eval_(`
      const cb = document.getElementById('SignupAgreement');
      if (cb && !cb.checked) { cb.click(); return 'checked TOS'; }
      return cb ? 'TOS already checked' : 'TOS not found';
    `);
    console.log("  TOS:", r);

    // Verify form state
    r = await eval_(`
      const email = (document.querySelector('input[type="email"]') || document.querySelector('input[placeholder="Email"]'))?.value || 'empty';
      const pass = document.querySelector('input[type="password"]')?.value?.length || 0;
      const fname = document.querySelector('input[placeholder="First Name"]')?.value || 'empty';
      const lname = document.querySelector('input[placeholder="Last Name"]')?.value || 'empty';
      return JSON.stringify({ email, passLength: pass, fname, lname });
    `);
    console.log("  Form:", r);

    // Submit
    console.log("\nStep 3: Submit...");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
        .find(b => b.textContent.includes('Join'));
      if (btn) { btn.click(); return 'clicked Join Freelancer'; }
      return 'submit not found';
    `);
    console.log("  ", r);
    await sleep(8000);

    // Check result
    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 600)
      });
    `);
    console.log("\n  Result:", r);
  } else {
    console.log("\nNot on the email form. May need to start over.");
    console.log("  Page:", state.preview?.substring(0, 300));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
