// Fix gig #3: set subcategory to Resume Writing and save
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.querySelector('textarea')?.value?.substring(0, 60) || '',
      categoryValues: Array.from(document.querySelectorAll('[class*="single-value"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim()),
      tags: Array.from(document.querySelectorAll('.react-tags__selected-tag-name'))
        .map(el => el.textContent.trim())
    });
  `);
  console.log("Current state:", r);

  // === SUBCATEGORY ===
  console.log("\n=== Setting Subcategory ===");

  // Find the subcategory dropdown - look for "Select A Subcategory" placeholder
  r = await eval_(`
    // Get all controls that look like category dropdowns
    const allControls = Array.from(document.querySelectorAll('[class*="category-selector__control"]'));
    const unique = allControls.filter(el => {
      // Only get the top-level control (not nested)
      return el.offsetParent !== null && !el.parentElement?.closest('[class*="category-selector__control"]');
    });
    return JSON.stringify(unique.map(el => ({
      text: el.textContent.trim().substring(0, 40),
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
      hasPlaceholder: !!el.querySelector('[class*="placeholder"]')
    })));
  `);
  console.log("Controls:", r);
  const ctrls = JSON.parse(r);

  // Find the one with placeholder "Select A Subcategory" or the second one
  const subCtrl = ctrls.find(c => c.hasPlaceholder || c.text.includes('Subcategory')) || ctrls[1];

  if (subCtrl) {
    console.log(`Clicking subcategory control at (${subCtrl.x}, ${subCtrl.y}): "${subCtrl.text}"`);
    await clickAt(send, subCtrl.x, subCtrl.y);
    await sleep(2000);

    // Find Resume Writing option
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && el.getBoundingClientRect().height > 5)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    const opts = JSON.parse(r);
    console.log("Options count:", opts.length, "First 5:", opts.slice(0, 5).map(o => o.text));

    const resume = opts.find(o => o.text === 'Resume Writing');
    if (resume) {
      console.log(`Clicking Resume Writing at (${resume.x}, ${resume.y})`);
      await clickAt(send, resume.x, resume.y);
      await sleep(2000);
      console.log("Selected Resume Writing!");
    } else {
      console.log("Resume Writing not found. All options:", opts.map(o => o.text));
    }
  } else {
    console.log("No subcategory control found!");
  }

  // Verify subcategory was set
  await sleep(500);
  r = await eval_(`
    return JSON.stringify({
      categoryValues: Array.from(document.querySelectorAll('[class*="single-value"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim()),
      placeholders: Array.from(document.querySelectorAll('[class*="placeholder"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim())
    });
  `);
  console.log("After subcategory:", r);

  // Wait for any service type to appear
  await sleep(1000);
  r = await eval_(`
    const svcWrapper = document.querySelector('.gig-service-type-wrapper');
    return svcWrapper ? 'service type found' : 'no service type';
  `);
  console.log("Service type:", r);

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
  await sleep(800);

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
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
