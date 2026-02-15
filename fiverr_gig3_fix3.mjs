// Fix gig #3 overview - fix category, subcategory, tags
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

  // ========== STEP 1: FIX CATEGORY ==========
  console.log("=== Fix Category ===");

  // Get the FIRST control (category dropdown)
  let r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="category-selector__control"]'))
      .filter(el => el.offsetParent !== null && !el.querySelector('[class*="control"]'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(controls);
  `);
  console.log("Controls:", r);
  const controls = JSON.parse(r);

  // Click the first control (category)
  if (controls.length > 0) {
    const catCtrl = controls[0];
    console.log(`Clicking category at (${catCtrl.x}, ${catCtrl.y}): "${catCtrl.text}"`);
    await clickAt(send, catCtrl.x, catCtrl.y);
    await sleep(1500);

    // Find and click "Writing & Translation"
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
    const catOpts = JSON.parse(r);
    console.log("Category options:", catOpts.map(o => o.text));
    const writing = catOpts.find(o => o.text.includes('Writing'));
    if (writing) {
      await clickAt(send, writing.x, writing.y);
      await sleep(2000);
      console.log("Selected:", writing.text);
    }
  }

  // ========== STEP 2: FIX SUBCATEGORY ==========
  console.log("\n=== Fix Subcategory ===");

  // After selecting category, get updated controls
  r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="category-selector__control"]'))
      .filter(el => el.offsetParent !== null && !el.querySelector('[class*="control"]'))
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(controls);
  `);
  console.log("Controls after category:", r);
  const controls2 = JSON.parse(r);

  // The second control should be subcategory
  if (controls2.length >= 2) {
    const subCtrl = controls2[1];
    console.log(`Clicking subcategory at (${subCtrl.x}, ${subCtrl.y}): "${subCtrl.text}"`);
    await clickAt(send, subCtrl.x, subCtrl.y);
    await sleep(1500);

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
    const subOpts = JSON.parse(r);
    console.log("Subcategory options:", subOpts.map(o => o.text));

    const resume = subOpts.find(o => o.text.includes('Resume'));
    if (resume) {
      await clickAt(send, resume.x, resume.y);
      await sleep(2000);
      console.log("Selected:", resume.text);
    } else {
      console.log("No Resume option! Scrolling in dropdown...");
      // Try scrolling the options list
      r = await eval_(`
        const menuList = document.querySelector('[class*="menu-list"]');
        if (menuList) { menuList.scrollTop = 500; return 'scrolled'; }
        return 'no menu-list';
      `);
      console.log(r);
      await sleep(500);
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
      const opts2 = JSON.parse(r);
      console.log("After scroll:", opts2.map(o => o.text));
      const resume2 = opts2.find(o => o.text.includes('Resume'));
      if (resume2) {
        await clickAt(send, resume2.x, resume2.y);
        await sleep(2000);
        console.log("Selected:", resume2.text);
      }
    }
  }

  // Verify category/subcategory
  r = await eval_(`
    const vals = Array.from(document.querySelectorAll('[class*="category-selector__single-value"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());
    return JSON.stringify(vals);
  `);
  console.log("Current values:", r);

  // ========== STEP 3: SERVICE TYPE ==========
  console.log("\n=== Service Type ===");
  await sleep(1000);
  r = await eval_(`
    const wrapper = document.querySelector('.gig-service-type-wrapper');
    if (!wrapper) return 'no wrapper found';
    const html = wrapper.innerHTML.substring(0, 200);
    return html;
  `);
  console.log("Service type wrapper:", r);

  // ========== STEP 4: CLEAR BAD TAGS AND ADD NEW ONES ==========
  console.log("\n=== Tags ===");

  // First remove any existing tags
  r = await eval_(`
    const removeBtns = Array.from(document.querySelectorAll('.react-tags__selected-tag'))
      .filter(el => el.offsetParent !== null);
    for (const btn of removeBtns) {
      btn.click();
      await new Promise(r => setTimeout(r, 200));
    }
    return 'removed ' + removeBtns.length;
  `);
  console.log("Removed tags:", r);
  await sleep(500);

  // Now add tags using focus + insertText + wait for suggestion
  r = await eval_(`
    const tagInput = document.querySelector('.react-tags__search-input input');
    if (tagInput) {
      tagInput.scrollIntoView({ block: 'center' });
      return JSON.stringify({
        x: Math.round(tagInput.getBoundingClientRect().x + 20),
        y: Math.round(tagInput.getBoundingClientRect().y + tagInput.getBoundingClientRect().height/2),
        value: tagInput.value
      });
    }
    return JSON.stringify({ error: 'no input' });
  `);
  console.log("Tag input:", r);
  const tagPos = JSON.parse(r);

  if (!tagPos.error) {
    const newTags = ["resume", "cover letter", "cv", "linkedin", "career"];

    for (const tag of newTags) {
      // Click input
      await clickAt(send, tagPos.x, tagPos.y);
      await sleep(200);

      // Focus input via JS to make sure it's focused
      await eval_(`
        const input = document.querySelector('.react-tags__search-input input');
        if (input) { input.focus(); input.value = ''; }
      `);
      await sleep(100);

      // Type using insertText
      await send("Input.insertText", { text: tag });
      await sleep(1500);

      // Check for suggestions
      r = await eval_(`
        const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(suggestions);
      `);
      const suggestions = JSON.parse(r);

      if (suggestions.length > 0) {
        // Click the best matching suggestion
        const exact = suggestions.find(s => s.text.toLowerCase() === tag.toLowerCase());
        const pick = exact || suggestions[0];
        await clickAt(send, pick.x, pick.y);
        console.log(`"${tag}" -> "${pick.text}"`);
      } else {
        // Try comma to separate (some tag systems use comma)
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: ",", code: "Comma" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: ",", code: "Comma" });
        await sleep(200);
        // Also try Enter
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
        console.log(`"${tag}" -> comma+enter (no suggestion)`);
      }
      await sleep(400);

      // Clear input for next tag
      await eval_(`
        const input = document.querySelector('.react-tags__search-input input');
        if (input) { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
      `);
      await sleep(200);
    }
  }

  // Verify tags
  await sleep(500);
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, .react-tags__selected-tag-name'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify(tags);
  `);
  console.log("Final tags:", r);

  // ========== STEP 5: METADATA ==========
  console.log("\n=== Metadata ===");
  await eval_(`window.scrollTo(0, document.documentElement.scrollHeight)`);
  await sleep(1000);

  r = await eval_(`
    // Look for any metadata section
    const metas = Array.from(document.querySelectorAll('[class*="metadata"], [class*="language"], [class*="attribute"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className || '').substring(0, 50),
        text: el.textContent.trim().substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x),
        y: Math.round(el.getBoundingClientRect().y)
      }));
    return JSON.stringify(metas.slice(0, 10));
  `);
  console.log("Metadata elements:", r);

  // ========== STEP 6: SAVE ==========
  console.log("\n=== Save ===");
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
