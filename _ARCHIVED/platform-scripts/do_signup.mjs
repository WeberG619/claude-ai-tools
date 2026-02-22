// Actually sign up on Freelancer.com
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

const EMAIL = process.argv[2];
const PASS = process.argv[3];
const FIRST = process.argv[4] || "Weber";
const LAST = process.argv[5] || "Gouin";

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found: ${urlMatch}`);
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

// Simulate realistic typing by setting value character by character via input events
async function typeInField(eval_, selector, value) {
  return await eval_(`
    const el = document.querySelector('${selector}');
    if (!el) return 'not found: ${selector}';
    el.focus();
    el.value = '';
    el.dispatchEvent(new Event('focus', { bubbles: true }));

    const val = ${JSON.stringify(value)};
    for (let i = 0; i < val.length; i++) {
      el.value = val.substring(0, i + 1);
      el.dispatchEvent(new Event('input', { bubbles: true }));
    }
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
    return 'typed: ' + el.value;
  `);
}

async function main() {
  console.log("=== Freelancer.com Signup ===\n");

  let { ws, send, eval_ } = await connectToTab("freelancer.com/signup");

  // Fill First Name
  console.log("Filling First Name...");
  let r = await typeInField(eval_, 'input[placeholder="First Name"]', FIRST);
  console.log("  ", r);
  await sleep(300);

  // Fill Last Name
  console.log("Filling Last Name...");
  r = await typeInField(eval_, 'input[placeholder="Last Name"]', LAST);
  console.log("  ", r);
  await sleep(300);

  // Fill Email
  console.log("Filling Email...");
  r = await typeInField(eval_, 'input[placeholder="Email"]', EMAIL);
  console.log("  ", r);
  await sleep(300);

  // Fill Password
  console.log("Filling Password...");
  r = await typeInField(eval_, 'input[placeholder="Password"]', PASS);
  console.log("  ", r);
  await sleep(300);

  // Check TOS checkbox
  console.log("Checking TOS...");
  r = await eval_(`
    const cb = document.getElementById('SignupAgreement');
    if (cb && !cb.checked) {
      cb.click();
      return 'checked';
    }
    return cb ? 'already checked' : 'not found';
  `);
  console.log("  ", r);
  await sleep(500);

  // Verify all fields before submit
  console.log("\nVerifying form...");
  r = await eval_(`
    const fname = document.querySelector('input[placeholder="First Name"]');
    const lname = document.querySelector('input[placeholder="Last Name"]');
    const email = document.querySelector('input[placeholder="Email"]');
    const pass = document.querySelector('input[placeholder="Password"]');
    const tos = document.getElementById('SignupAgreement');
    return JSON.stringify({
      firstName: fname?.value || 'empty',
      lastName: lname?.value || 'empty',
      email: email?.value || 'empty',
      passLength: pass?.value?.length || 0,
      tosChecked: tos?.checked || false
    });
  `);
  console.log("  ", r);

  // Click "Join Freelancer" submit button
  console.log("\nSubmitting...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
      .find(b => b.textContent.includes('Join Freelancer'));
    if (btn) { btn.click(); return 'clicked Join Freelancer'; }
    return 'submit button not found';
  `);
  console.log("  ", r);
  await sleep(8000);

  // Check result
  console.log("\nChecking result...");
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], [class*="alert"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 150))
        .filter(t => t.length > 0),
      pagePreview: document.body.innerText.substring(0, 800)
    }, null, 2);
  `);
  console.log("  Result:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
