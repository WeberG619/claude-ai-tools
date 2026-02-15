// Fix gig #3 pricing using React-compatible value setting
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

async function selectPenta(send, eval_, dropdownX, dropdownY, optionText) {
  await clickAt(send, dropdownX, dropdownY);
  await sleep(600);
  const r = await eval_(`
    const opts = Array.from(document.querySelectorAll('.table-select-option'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(opts);
  `);
  const opts = JSON.parse(r);
  const target = opts.find(o => o.text.toLowerCase().includes(optionText.toLowerCase()));
  if (target) {
    await clickAt(send, target.x, target.y);
    await sleep(400);
    return target.text;
  }
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
  return `NOT FOUND: "${optionText}"`;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Scroll to top
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // === PACKAGE TITLES ===
  console.log("=== Package Titles ===");
  let r = await eval_(`
    const titles = document.querySelectorAll('.pkg-title-input');
    return JSON.stringify(Array.from(titles).filter(el => el.offsetParent !== null).map(el => ({
      value: el.value,
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    })));
  `);
  console.log("Titles:", r);
  const titleInputs = JSON.parse(r);
  const titles = ["Basic", "Standard", "Premium"];

  for (let i = 0; i < Math.min(titleInputs.length, 3); i++) {
    // Click to focus
    await clickAt(send, titleInputs[i].x, titleInputs[i].y);
    await sleep(200);
    // Select all
    await tripleClick(send, titleInputs[i].x, titleInputs[i].y);
    await sleep(100);
    // Type
    await send("Input.insertText", { text: titles[i] });
    // Tab out to trigger blur/change
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(200);
    console.log(`  Title ${i+1}: "${titles[i]}"`);
  }

  // Verify titles were set
  r = await eval_(`
    const titles = document.querySelectorAll('.pkg-title-input');
    return JSON.stringify(Array.from(titles).filter(el => el.offsetParent !== null).map(el => el.value));
  `);
  console.log("Titles verify:", r);

  // === PACKAGE DESCRIPTIONS ===
  console.log("\n=== Package Descriptions ===");
  r = await eval_(`
    const descs = document.querySelectorAll('.pkg-description-input');
    return JSON.stringify(Array.from(descs).filter(el => el.offsetParent !== null).map(el => ({
      value: el.value,
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    })));
  `);
  const descInputs = JSON.parse(r);
  const descs = [
    "Professional resume with keyword optimization",
    "Resume plus cover letter for your target role",
    "Resume, cover letter, and LinkedIn profile"
  ];

  for (let i = 0; i < Math.min(descInputs.length, 3); i++) {
    await clickAt(send, descInputs[i].x, descInputs[i].y);
    await sleep(200);
    await tripleClick(send, descInputs[i].x, descInputs[i].y);
    await sleep(100);
    await send("Input.insertText", { text: descs[i] });
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(200);
    console.log(`  Desc ${i+1}: "${descs[i]}"`);
  }

  // === DELIVERY TIMES ===
  console.log("\n=== Delivery Times ===");
  r = await eval_(`
    const dd = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && !el.querySelector('.select-penta-design')
        && el.textContent.trim().includes('Delivery') && el.getBoundingClientRect().y > 0 && el.getBoundingClientRect().y < 1200)
      .map(el => ({
        text: el.textContent.trim().substring(0, 20),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(dd);
  `);
  const dd = JSON.parse(r);
  const delivTimes = ["3 days", "2 days", "1 day"];
  for (let i = 0; i < Math.min(dd.length, 3); i++) {
    const result = await selectPenta(send, eval_, dd[i].x, dd[i].y, delivTimes[i]);
    console.log(`  Delivery ${i+1}: ${result}`);
  }

  // === REVISIONS ===
  console.log("\n=== Revisions ===");
  r = await eval_(`
    const rd = Array.from(document.querySelectorAll('.select-penta-design'))
      .filter(el => el.offsetParent !== null && !el.querySelector('.select-penta-design')
        && (el.textContent.trim() === 'Select' || /^\\d+$/.test(el.textContent.trim()) || el.textContent.trim() === 'UNLIMITED')
        && el.getBoundingClientRect().y > 0 && el.getBoundingClientRect().y < 1200)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(rd);
  `);
  const rd = JSON.parse(r);
  const revisions = ["1", "2", "unlimited"];
  for (let i = 0; i < Math.min(rd.length, 3); i++) {
    if (rd[i].text.toLowerCase() === revisions[i].toLowerCase()) {
      console.log(`  Revision ${i+1}: already set to "${rd[i].text}"`);
    } else {
      const result = await selectPenta(send, eval_, rd[i].x, rd[i].y, revisions[i]);
      console.log(`  Revision ${i+1}: ${result}`);
    }
  }

  // === PRICES ===
  console.log("\n=== Prices ===");
  r = await eval_(`
    const pp = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        value: el.value,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(pp);
  `);
  const pp = JSON.parse(r);
  const prices = ["15", "30", "60"];

  for (let i = 0; i < Math.min(pp.length, 3); i++) {
    await clickAt(send, pp[i].x, pp[i].y);
    await sleep(200);
    await tripleClick(send, pp[i].x, pp[i].y);
    await sleep(100);
    await send("Input.insertText", { text: prices[i] });
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
    await sleep(300);
    console.log(`  Price ${i+1}: $${prices[i]}`);
  }

  // Verify prices
  r = await eval_(`
    return JSON.stringify(Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null).map(el => el.value));
  `);
  console.log("Prices verify:", r);

  // === UNCHECK ALL EXTRAS ===
  console.log("\n=== Uncheck Extras ===");
  // Scroll down to extras
  await eval_(`window.scrollTo(0, 1500)`);
  await sleep(500);

  for (let attempt = 0; attempt < 10; attempt++) {
    r = await eval_(`
      const checkedExtras = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && el.checked
            && !el.classList.contains('pkgs-toggler')
            && rect.x < 300  // Extras column (x~168)
            && rect.y > 0;
        })
        .map(el => {
          const label = el.closest('[class*="extra"], [class*="addon"], tr, div, li')?.textContent?.trim()?.substring(0, 30) || '';
          return {
            label,
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + 10)
          };
        });
      return JSON.stringify(checkedExtras);
    `);
    const extras = JSON.parse(r);
    if (extras.length === 0) break;
    console.log(`  Unchecking: "${extras[0].label}" at (${extras[0].x}, ${extras[0].y})`);
    await clickAt(send, extras[0].x, extras[0].y);
    await sleep(500);
  }

  // Verify no extras checked
  r = await eval_(`
    const checked = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null && el.checked && !el.classList.contains('pkgs-toggler') && el.getBoundingClientRect().x < 300);
    return 'Checked extras: ' + checked.length;
  `);
  console.log(r);

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
        errors
      });
    `);
    console.log("After save:", r);

    // If still wizard=1 with no errors, navigate to wizard=2
    const state = JSON.parse(r);
    if (state.wizard === '1' && state.errors.length === 0) {
      console.log("\nNavigating to wizard=2...");
      await eval_(`window.location.href = location.href.replace('wizard=1', 'wizard=2')`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard')
        });
      `);
      console.log("After nav:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
