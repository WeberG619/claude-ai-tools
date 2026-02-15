// Final attempt to set revisions, verify prices and word counts, then save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll to revisions area
  await eval_(`window.scrollTo(0, 500)`);
  await sleep(500);

  // Set revisions for all 3 packages using indexed approach
  console.log("=== Setting Revisions ===");

  for (let pkgIdx = 0; pkgIdx < 3; pkgIdx++) {
    // Check current value
    let r = await eval_(`
      const drops = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 0 && rect.y < 1500 && !el.className.includes('duration');
        });
      if (drops[${pkgIdx}]) {
        return drops[${pkgIdx}].textContent.trim().substring(0, 20);
      }
      return 'not found';
    `);
    console.log(`Package ${pkgIdx} revision: ${r}`);

    if (r === 'UNLIMITED') continue;

    // Click to open this specific dropdown
    r = await eval_(`
      const drops = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 0 && rect.y < 1500 && !el.className.includes('duration');
        });
      const drop = drops[${pkgIdx}];
      if (drop) {
        drop.scrollIntoView({ block: 'center' });
        const rect = drop.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    await sleep(300);
    const dropPos = JSON.parse(r);
    if (dropPos.error) continue;

    console.log(`  Opening dropdown at (${dropPos.x}, ${dropPos.y})`);
    await clickAt(send, dropPos.x, dropPos.y);
    await sleep(1000);

    // Find the UNLIMITED option that's now visible and near this dropdown
    r = await eval_(`
      const unlimitedBtns = Array.from(document.querySelectorAll('.table-select-option, button'))
        .filter(el => {
          const text = el.textContent.trim();
          const rect = el.getBoundingClientRect();
          return text === 'UNLIMITED' && el.offsetParent !== null && rect.y > 0 && rect.y < 2000;
        })
        .map(el => {
          const rect = el.getBoundingClientRect();
          el.scrollIntoView({ block: 'nearest' });
          return {
            x: Math.round(rect.x + rect.width/2),
            y: Math.round(rect.y + rect.height/2)
          };
        });
      return JSON.stringify(unlimitedBtns);
    `);
    console.log(`  UNLIMITED buttons: ${r}`);
    const unlBtns = JSON.parse(r);

    if (unlBtns.length > 0) {
      // Wait for scroll to settle
      await sleep(300);

      // Get fresh position after scroll
      r = await eval_(`
        const unlimitedBtns = Array.from(document.querySelectorAll('.table-select-option, button'))
          .filter(el => el.textContent.trim() === 'UNLIMITED' && el.offsetParent !== null && el.getBoundingClientRect().y > 0);
        if (unlimitedBtns.length > 0) {
          const btn = unlimitedBtns[0];
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      const freshPos = JSON.parse(r);
      if (!freshPos.error) {
        console.log(`  Clicking UNLIMITED at (${freshPos.x}, ${freshPos.y})`);
        await clickAt(send, freshPos.x, freshPos.y);
        await sleep(500);
      }
    }

    // Verify
    r = await eval_(`
      const drops = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 0 && rect.y < 1500 && !el.className.includes('duration');
        });
      return drops[${pkgIdx}]?.textContent?.trim()?.substring(0, 20) || 'unknown';
    `);
    console.log(`  Now: ${r}`);
  }

  // Set word counts using React native setter
  console.log("\n=== Setting Word Counts ===");
  let r = await eval_(`
    const wordInputs = Array.from(document.querySelectorAll('input[type="number"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && !el.className.includes('price');
      })
      .slice(0, 3); // First 3 number inputs (not price)

    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const counts = ['1000', '3000', '5000'];

    wordInputs.forEach((input, i) => {
      nativeSetter.call(input, counts[i] || '1000');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    return JSON.stringify(wordInputs.map(el => el.value));
  `);
  console.log("Words:", r);

  // Set prices using React native setter
  console.log("\n=== Setting Prices ===");
  r = await eval_(`
    const priceInputs = Array.from(document.querySelectorAll('.price-input, input[class*="price"]'))
      .filter(el => el.offsetParent !== null)
      .slice(0, 3);

    const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const prices = ['10', '25', '50'];

    priceInputs.forEach((input, i) => {
      nativeSetter.call(input, prices[i] || '10');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.dispatchEvent(new Event('change', { bubbles: true }));
    });
    return JSON.stringify(priceInputs.map(el => el.value));
  `);
  console.log("Prices:", r);

  // Summary of all pricing data
  console.log("\n=== Summary ===");
  r = await eval_(`
    const deliveries = Array.from(document.querySelectorAll('.select-penta-design.pkg-duration-input.table-select'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
      .map(el => el.textContent.trim().substring(0, 20));

    const revisions = Array.from(document.querySelectorAll('.select-penta-design.table-select'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0 && !el.className.includes('duration'))
      .map(el => el.textContent.trim().substring(0, 20));

    const prices = Array.from(document.querySelectorAll('.price-input'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.value);

    const wordInputs = Array.from(document.querySelectorAll('input[type="number"]'))
      .filter(el => el.offsetParent !== null && !el.className.includes('price'))
      .slice(0, 3)
      .map(el => el.value);

    return JSON.stringify({ deliveries, revisions, prices, words: wordInputs });
  `);
  console.log(r);

  // Scroll to save
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
    console.log(`\nClicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(6000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: (document.body?.innerText || '').substring(0, 1000)
      });
    `);
    const result = JSON.parse(r);
    console.log("URL:", result.url);
    console.log("Wizard:", result.wizard);
    console.log("Body:", result.body.substring(0, 500));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
