// Fill new Fiverr gig #2 - Writing/Proofreading - Overview
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs/new"));
  if (!tab) throw new Error("New gig page not found");
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

  // Step 1: Fill title
  console.log("=== Filling Title ===");
  let r = await eval_(`
    const ta = document.querySelector('.gig-title-textarea');
    if (ta) {
      ta.focus();
      const rect = ta.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + 10) });
    }
    return JSON.stringify({ error: 'no textarea' });
  `);
  const ta = JSON.parse(r);
  if (!ta.error) {
    await clickAt(send, ta.x, ta.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    await send("Input.insertText", { text: "I will do professional proofreading, editing, and rewriting of your content" });
    await sleep(500);
  }

  // Verify title
  r = await eval_(`return document.querySelector('input[name="gig[title]"]')?.value || ''`);
  console.log("Title hidden value:", r);

  // Step 2: Select Category - Writing & Translation
  console.log("\n=== Selecting Category ===");
  // Click the category dropdown
  r = await eval_(`
    const catDrop = document.querySelector('.gig-category .orca-combo-box-container, .generic-category-dropdown.gig-categ');
    if (catDrop) {
      const rect = catDrop.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no category dropdown' });
  `);
  console.log("Category dropdown:", r);
  const catDrop = JSON.parse(r);

  if (!catDrop.error) {
    await clickAt(send, catDrop.x, catDrop.y);
    await sleep(1000);

    // Type "Writing" to filter
    await send("Input.insertText", { text: "Writing" });
    await sleep(1000);

    // Click the Writing & Translation option
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => el.textContent.includes('Writing') && el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    console.log("Writing options:", r);
    const opts = JSON.parse(r);

    if (opts.length > 0) {
      const writing = opts.find(o => o.text.includes('Writing & Translation')) || opts[0];
      console.log(`Clicking "${writing.text}"`);
      await clickAt(send, writing.x, writing.y);
      await sleep(2000);
    }
  }

  // Verify category
  r = await eval_(`return document.querySelector('input[name="gig[category_id]"]')?.value || ''`);
  console.log("Category ID:", r);

  // Step 3: Select Subcategory - Proofreading & Editing
  console.log("\n=== Selecting Subcategory ===");
  r = await eval_(`
    const subDrop = document.querySelector('.gig-subcategory .orca-combo-box-container, .generic-category-dropdown.gig-subca');
    if (subDrop) {
      const rect = subDrop.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no subcategory dropdown' });
  `);
  console.log("Subcategory dropdown:", r);
  const subDrop = JSON.parse(r);

  if (!subDrop.error) {
    await clickAt(send, subDrop.x, subDrop.y);
    await sleep(1000);

    await send("Input.insertText", { text: "Proofreading" });
    await sleep(1000);

    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[class*="option"]'))
        .filter(el => (el.textContent.includes('Proofreading') || el.textContent.includes('Editing')) && el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    console.log("Proofreading options:", r);
    const subOpts = JSON.parse(r);

    if (subOpts.length > 0) {
      console.log(`Clicking "${subOpts[0].text}"`);
      await clickAt(send, subOpts[0].x, subOpts[0].y);
      await sleep(2000);
    }
  }

  r = await eval_(`return document.querySelector('input[name="gig[sub_category_id]"]')?.value || ''`);
  console.log("Subcategory ID:", r);

  // Step 4: Add tags via react-tags
  console.log("\n=== Adding Tags ===");
  const tags = ["proofreading", "editing", "rewriting", "content writing", "grammar check"];

  for (const tag of tags) {
    r = await eval_(`
      const input = document.querySelector('.react-tags__search-input input');
      if (input) {
        input.focus();
        const rect = input.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no tag input' });
    `);
    const tagInput = JSON.parse(r);
    if (tagInput.error) break;

    await clickAt(send, tagInput.x, tagInput.y);
    await sleep(200);
    await send("Input.insertText", { text: tag });
    await sleep(800);

    // Click first suggestion or press Enter
    r = await eval_(`
      const suggestion = document.querySelector('.react-tags__suggestions li');
      if (suggestion) {
        suggestion.click();
        return 'clicked suggestion: ' + suggestion.textContent.trim().substring(0, 30);
      }
      return 'no suggestion';
    `);
    console.log(`Tag "${tag}":`, r);

    if (r === 'no suggestion') {
      // Try Enter key
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      console.log("  Pressed Enter");
    }
    await sleep(500);
  }

  // Verify tags
  r = await eval_(`return document.querySelector('input[name="gig[tag_list]"]')?.value || ''`);
  console.log("\nTag list:", r);

  // Check all hidden fields
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || ''
    });
  `);
  console.log("\n=== Overview Summary ===");
  console.log(r);

  // Click Save & Continue
  console.log("\n=== Save & Continue ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("Save button:", r);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error && !saveBtn.disabled) {
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        body: (document.body?.innerText || '').substring(0, 500)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
