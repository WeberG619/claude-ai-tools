// Fix email and resubmit Freelancer signup
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const EMAIL = process.argv[2];
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
  console.log("Connected\n");

  // Clear and re-enter correct email
  console.log("Fixing email...");
  let r = await eval_(`
    const emailInput = document.querySelector('input[type="email"]') || document.querySelector('input[placeholder="Email"]');
    if (!emailInput) return 'email input not found';

    // Clear it
    emailInput.focus();
    emailInput.value = '';
    emailInput.dispatchEvent(new Event('input', { bubbles: true }));

    // Type the correct email
    const email = ${JSON.stringify(EMAIL)};
    for (let i = 0; i < email.length; i++) {
      emailInput.value = email.substring(0, i + 1);
      emailInput.dispatchEvent(new Event('input', { bubbles: true }));
    }
    emailInput.dispatchEvent(new Event('change', { bubbles: true }));
    emailInput.dispatchEvent(new Event('blur', { bubbles: true }));
    return 'email corrected to: ' + emailInput.value;
  `);
  console.log("  ", r);
  await sleep(300);

  // Verify password is still filled
  r = await eval_(`
    const pass = document.querySelector('input[type="password"]');
    if (!pass) return 'password field not found';
    if (pass.value.length > 0) return 'password still filled (' + pass.value.length + ' chars)';

    // Re-enter password
    pass.focus();
    const pw = ${JSON.stringify(PASS)};
    pass.value = pw;
    pass.dispatchEvent(new Event('input', { bubbles: true }));
    pass.dispatchEvent(new Event('change', { bubbles: true }));
    return 'password re-entered';
  `);
  console.log("  Password:", r);

  // Verify TOS
  r = await eval_(`
    const cb = document.getElementById('SignupAgreement');
    if (!cb) return 'TOS not found';
    if (!cb.checked) { cb.click(); return 'checked TOS'; }
    return 'TOS already checked';
  `);
  console.log("  TOS:", r);

  // Verify all fields
  console.log("\nForm state:");
  r = await eval_(`
    const fname = document.querySelector('input[placeholder="First Name"]')?.value || '';
    const lname = document.querySelector('input[placeholder="Last Name"]')?.value || '';
    const email = (document.querySelector('input[type="email"]') || document.querySelector('input[placeholder="Email"]'))?.value || '';
    const pass = document.querySelector('input[type="password"]')?.value?.length || 0;
    const tos = document.getElementById('SignupAgreement')?.checked || false;
    return JSON.stringify({ firstName: fname, lastName: lname, email, passLength: pass, tosChecked: tos });
  `);
  console.log("  ", r);

  // Submit
  console.log("\nSubmitting...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button[type="submit"]'))
      .find(b => b.textContent.includes('Join'));
    if (btn) { btn.click(); return 'clicked Join Freelancer'; }
    return 'submit not found';
  `);
  console.log("  ", r);
  await sleep(10000);

  // Check result
  console.log("\nResult:");
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3),
      preview: document.body.innerText.substring(0, 600)
    }, null, 2);
  `);
  console.log("  ", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
