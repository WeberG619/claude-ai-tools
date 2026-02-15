// Fill gig #3 overview: Resume & CV Writing
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

  // === TITLE ===
  console.log("=== Title ===");
  let r = await eval_(`
    const input = document.querySelector('.gig-title-input textarea, textarea');
    if (input) {
      input.scrollIntoView({ block: 'center' });
      const rect = input.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no textarea' });
  `);
  const titlePos = JSON.parse(r);
  if (!titlePos.error) {
    await tripleClick(send, titlePos.x, titlePos.y);
    await sleep(200);
    await send("Input.insertText", { text: "write a professional resume, CV, and cover letter that gets interviews" });
    await sleep(500);
    console.log("Title set");
  }

  // === CATEGORY: Writing & Translation ===
  console.log("\n=== Category ===");
  r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="control"]'))
      .filter(el => {
        const parent = el.closest('.orca-combo-box, [class*="category"]');
        return parent && el.offsetParent !== null && el.getBoundingClientRect().y > 0;
      });
    if (controls.length > 0) {
      const ctrl = controls[0];
      ctrl.scrollIntoView({ block: 'center' });
      const rect = ctrl.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no control' });
  `);
  console.log("Category control:", r);
  const catCtrl = JSON.parse(r);

  if (!catCtrl.error) {
    await sleep(300);
    await clickAt(send, catCtrl.x, catCtrl.y);
    await sleep(1000);

    // Find "Writing & Translation"
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => el.textContent.trim().includes('Writing') && el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    console.log("Options:", r);
    const opts = JSON.parse(r);
    const writing = opts.find(o => o.text.includes('Writing'));
    if (writing) {
      await clickAt(send, writing.x, writing.y);
      await sleep(1500);
      console.log("Selected Writing & Translation");
    }
  }

  // === SUBCATEGORY: Resume Writing ===
  console.log("\n=== Subcategory ===");
  await sleep(500);
  r = await eval_(`
    const combos = Array.from(document.querySelectorAll('.orca-combo-box'));
    if (combos.length >= 2) {
      const ctrl = combos[1].querySelector('[class*="control"]');
      if (ctrl) {
        ctrl.scrollIntoView({ block: 'center' });
        const rect = ctrl.getBoundingClientRect();
        return JSON.stringify({ text: ctrl.textContent.trim().substring(0, 30), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
    }
    return JSON.stringify({ error: 'no subcategory' });
  `);
  console.log("Subcategory:", r);
  const subCtrl = JSON.parse(r);

  if (!subCtrl.error) {
    await clickAt(send, subCtrl.x, subCtrl.y);
    await sleep(1000);

    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    console.log("Sub options:", r);
    const subOpts = JSON.parse(r);
    const resume = subOpts.find(o => o.text.includes('Resume'));
    if (resume) {
      await clickAt(send, resume.x, resume.y);
      await sleep(1000);
      console.log("Selected:", resume.text);
    }
  }

  // === SERVICE TYPE ===
  console.log("\n=== Service Type ===");
  await sleep(500);
  r = await eval_(`
    const wrapper = document.querySelector('.gig-service-type-wrapper');
    if (wrapper) {
      const select = wrapper.querySelector('select');
      if (select) {
        return JSON.stringify({ tag: 'SELECT', options: Array.from(select.options).map(o => o.text) });
      }
      const dropdown = wrapper.querySelector('[class*="control"], [class*="select"]');
      if (dropdown) {
        dropdown.scrollIntoView({ block: 'center' });
        const rect = dropdown.getBoundingClientRect();
        return JSON.stringify({ tag: 'DROPDOWN', x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: dropdown.textContent.trim().substring(0, 30) });
      }
    }
    return JSON.stringify({ error: 'no service type' });
  `);
  console.log("Service type:", r);
  const svcType = JSON.parse(r);

  if (svcType.tag === 'DROPDOWN' || svcType.tag === 'SELECT') {
    if (svcType.x) {
      await clickAt(send, svcType.x, svcType.y);
      await sleep(800);

      r = await eval_(`
        const opts = Array.from(document.querySelectorAll('.gig-service-type-wrapper option, .gig-service-type-wrapper [class*="option"]'))
          .filter(el => el.offsetParent !== null || el.tagName === 'OPTION')
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            value: el.value || '',
            x: Math.round((el.getBoundingClientRect().x || 0) + (el.getBoundingClientRect().width || 0)/2),
            y: Math.round((el.getBoundingClientRect().y || 0) + (el.getBoundingClientRect().height || 0)/2)
          }));
        return JSON.stringify(opts);
      `);
      console.log("Service options:", r);
      const svcOpts = JSON.parse(r);
      // Pick "Resume" or first available
      const resumeSvc = svcOpts.find(o => o.text.includes('Resume')) || svcOpts.find(o => o.text.includes('CV')) || svcOpts[0];
      if (resumeSvc && resumeSvc.y > 0) {
        await clickAt(send, resumeSvc.x, resumeSvc.y);
        await sleep(500);
        console.log("Selected service:", resumeSvc.text);
      }
    }
  }

  // === TAGS ===
  console.log("\n=== Tags ===");
  r = await eval_(`
    const tagInput = document.querySelector('.react-tags__search-input input');
    if (tagInput) {
      tagInput.scrollIntoView({ block: 'center' });
      const rect = tagInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no tag input' });
  `);
  const tagPos = JSON.parse(r);

  if (!tagPos.error) {
    const tags = ["resume writing", "cv writing", "cover letter", "linkedin profile", "career"];
    for (const tag of tags) {
      await clickAt(send, tagPos.x, tagPos.y);
      await sleep(300);
      await send("Input.insertText", { text: tag });
      await sleep(800);

      r = await eval_(`
        const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(suggestions);
      `);
      const suggestions = JSON.parse(r);
      if (suggestions.length > 0) {
        await clickAt(send, suggestions[0].x, suggestions[0].y);
        console.log(`Tag "${tag}" -> "${suggestions[0].text}"`);
      } else {
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
        console.log(`Tag "${tag}" -> Enter`);
      }
      await sleep(500);
    }
  }

  // === METADATA: English ===
  console.log("\n=== Metadata ===");
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        const label = (el.closest('label') || el.parentElement)?.textContent?.trim() || '';
        return label.includes('English') && el.offsetParent !== null;
      });
    if (checkboxes.length > 0 && !checkboxes[0].checked) {
      checkboxes[0].scrollIntoView({ block: 'center' });
      const rect = checkboxes[0].getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + 10), checked: false });
    }
    return JSON.stringify({ checked: checkboxes.length > 0 ? checkboxes[0].checked : 'not found' });
  `);
  console.log("English:", r);
  const eng = JSON.parse(r);
  if (eng.x) {
    await clickAt(send, eng.x, eng.y);
    await sleep(300);
    console.log("English checked");
  }

  // === SAVE ===
  console.log("\n=== Save Overview ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) { btn.scrollIntoView({ behavior: 'smooth', block: 'center' }); return 'found'; }
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
