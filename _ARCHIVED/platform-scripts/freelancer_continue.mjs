// Continue Freelancer.com signup - select account type and complete
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com");
  console.log("Connected\n");

  // Step 1: Select "Earn money freelancing"
  console.log("Step 1: Select 'Earn money freelancing'...");
  let r = await eval_(`
    // Find the freelancing option
    const options = Array.from(document.querySelectorAll('button, div[role="button"], a, label, [class*="card"], [class*="option"]'));
    const freelance = options.find(el => el.textContent.includes('Earn money freelancing'));
    if (freelance) { freelance.click(); return 'clicked Earn money freelancing'; }
    // Try finding by radio or other selectors
    const radios = Array.from(document.querySelectorAll('input[type="radio"]'));
    for (const radio of radios) {
      const parent = radio.closest('label') || radio.parentElement?.parentElement;
      if (parent?.textContent?.includes('freelancing')) {
        radio.click();
        return 'clicked freelancing radio';
      }
    }
    return 'not found. Options: ' + options.filter(o => o.offsetParent !== null).map(o => o.textContent.trim().substring(0, 40)).join(' | ');
  `);
  console.log("  ", r);
  await sleep(2000);

  // Check for Next button and click it
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Next') || b.textContent.trim().includes('Continue'));
    if (btn) { btn.click(); return 'clicked ' + btn.textContent.trim(); }
    return 'no next button';
  `);
  console.log("  ", r);
  await sleep(5000);

  // Step 2: Check what's next
  console.log("\nStep 2: Check next page...");
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      pagePreview: document.body.innerText.substring(0, 1000),
      inputs: Array.from(document.querySelectorAll('input')).filter(i => i.offsetParent !== null).map(i => ({
        type: i.type, placeholder: i.placeholder, name: i.name
      })),
      buttons: Array.from(document.querySelectorAll('button')).filter(b => b.offsetParent !== null).map(b => ({
        text: b.textContent.trim().substring(0, 50)
      }))
    }, null, 2);
  `);
  console.log("  ", r);

  // Step 3: Handle whatever comes next (skills, profile info, etc.)
  const pageState = JSON.parse(r);
  const preview = pageState.pagePreview;

  if (preview.includes('skill') || preview.includes('Skill') || preview.includes('What are you')) {
    console.log("\nStep 3: Skills selection...");
    // Select relevant skills
    r = await eval_(`
      const input = document.querySelector('input[type="text"]:not([type="hidden"])');
      if (input) {
        // Type skill into search
        const skills = ['Content Writing', 'Data Entry', 'Research', 'Technical Writing', 'Excel'];
        input.focus();
        input.value = skills[0];
        input.dispatchEvent(new Event('input', { bubbles: true }));
        return 'typed skill: ' + skills[0];
      }
      // Check for skill chips/tags to click
      const chips = Array.from(document.querySelectorAll('[class*="chip"], [class*="tag"], [class*="skill"]'))
        .filter(c => c.offsetParent !== null);
      return 'chips found: ' + chips.length + ' - ' + chips.map(c => c.textContent.trim().substring(0, 30)).join(', ');
    `);
    console.log("  ", r);
  }

  if (preview.includes('email') || preview.includes('verify') || preview.includes('Verify')) {
    console.log("\nEmail verification needed!");
  }

  if (preview.includes('Dashboard') || preview.includes('Welcome')) {
    console.log("\nSignup COMPLETE! Welcome to Freelancer.com!");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
