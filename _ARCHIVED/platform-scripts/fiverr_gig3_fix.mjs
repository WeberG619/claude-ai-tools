// Fix subcategory, service type, tags, metadata for gig #3
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
    const catVal = document.querySelector('[name*="category"]')?.value ||
                   document.querySelector('.orca-combo-box')?.textContent?.trim()?.substring(0, 30) || '';
    return JSON.stringify({
      url: location.href,
      category: catVal,
      title: document.querySelector('textarea')?.value?.substring(0, 60) || ''
    });
  `);
  console.log("State:", r);

  // === FIX SUBCATEGORY ===
  console.log("\n=== Subcategory ===");

  // Check how many combo boxes exist
  r = await eval_(`
    const combos = Array.from(document.querySelectorAll('.orca-combo-box'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        class: (el.className || '').substring(0, 60)
      }));
    return JSON.stringify(combos);
  `);
  console.log("Combo boxes:", r);
  const combos = JSON.parse(r);

  // The second combo should be subcategory
  if (combos.length >= 2) {
    const subCombo = combos[1];
    console.log(`Clicking subcategory at (${subCombo.x}, ${subCombo.y}): "${subCombo.text}"`);
    await clickAt(send, subCombo.x, subCombo.y);
    await sleep(1500);

    // Look for Resume Writing option
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
    console.log("Subcategory options:", r);
    const subOpts = JSON.parse(r);
    const resume = subOpts.find(o => o.text.includes('Resume'));
    if (resume) {
      await clickAt(send, resume.x, resume.y);
      await sleep(1000);
      console.log("Selected:", resume.text);
    } else if (subOpts.length > 0) {
      console.log("No Resume option found, first options:", subOpts.slice(0, 5).map(o => o.text));
    }
  }

  // === SERVICE TYPE ===
  console.log("\n=== Service Type ===");
  await sleep(500);
  r = await eval_(`
    const wrapper = document.querySelector('.gig-service-type-wrapper');
    if (!wrapper) return JSON.stringify({ error: 'no wrapper' });
    const allEls = Array.from(wrapper.querySelectorAll('*'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 40),
        text: el.textContent.trim().substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(allEls.slice(0, 15));
  `);
  console.log("Service type elements:", r);

  // Try clicking the service type dropdown
  r = await eval_(`
    const wrapper = document.querySelector('.gig-service-type-wrapper');
    if (wrapper) {
      const selectable = wrapper.querySelector('select, [class*="select"], [class*="control"], [class*="dropdown"]');
      if (selectable) {
        selectable.scrollIntoView({ block: 'center' });
        const rect = selectable.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), tag: selectable.tagName });
      }
    }
    return JSON.stringify({ error: 'nothing to click' });
  `);
  console.log("Service type clickable:", r);
  const svcClick = JSON.parse(r);
  if (!svcClick.error) {
    await clickAt(send, svcClick.x, svcClick.y);
    await sleep(800);

    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('.gig-service-type-wrapper li, .gig-service-type-wrapper [class*="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    console.log("Service options:", r);
    const svcOpts = JSON.parse(r);
    if (svcOpts.length > 0) {
      const pick = svcOpts.find(o => o.text.includes('Resume') || o.text.includes('CV')) || svcOpts[0];
      await clickAt(send, pick.x, pick.y);
      await sleep(500);
      console.log("Selected service:", pick.text);
    }
  }

  // === FIX TAGS ===
  console.log("\n=== Tags ===");
  // Check current tags
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(tags);
  `);
  console.log("Current tags:", r);
  const currentTags = JSON.parse(r);

  if (currentTags.length < 3) {
    // Clear existing tag input first
    r = await eval_(`
      const tagInput = document.querySelector('.react-tags__search-input input');
      if (tagInput) {
        tagInput.value = '';
        tagInput.scrollIntoView({ block: 'center' });
        const rect = tagInput.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no input' });
    `);
    const tagPos = JSON.parse(r);

    if (!tagPos.error) {
      const newTags = ["resume", "cover letter", "cv writing", "job search", "career"];
      for (const tag of newTags) {
        if (currentTags.length + newTags.indexOf(tag) >= 5) break;

        // Click input, clear it, type tag
        await clickAt(send, tagPos.x, tagPos.y);
        await sleep(200);
        // Select all and delete any leftover text
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(200);

        // Type the tag
        for (const char of tag) {
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, code: `Key${char.toUpperCase()}` });
          await sleep(30);
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: char, code: `Key${char.toUpperCase()}` });
          await sleep(30);
        }
        await sleep(1000);

        // Check for suggestions
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
          console.log(`"${tag}" -> "${suggestions[0].text}"`);
        } else {
          // Press Enter
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
          console.log(`"${tag}" -> Enter (no suggestion)`);
        }
        await sleep(500);
      }
    }
  }

  // Verify tags
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(tags);
  `);
  console.log("Tags after fix:", r);

  // === METADATA ===
  console.log("\n=== Metadata ===");
  r = await eval_(`
    const metaSection = document.querySelector('.metadata-names-list, [class*="metadata"]');
    if (metaSection) {
      metaSection.scrollIntoView({ block: 'center' });
      return metaSection.textContent.trim().substring(0, 100);
    }
    return 'not found';
  `);
  console.log("Metadata section:", r);

  // Try to find and check English
  await sleep(500);
  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => {
        const parent = el.closest('label, li, div');
        const text = parent?.textContent?.trim() || '';
        return text === 'English' || text.startsWith('English');
      });
    if (checkboxes.length > 0) {
      if (!checkboxes[0].checked) {
        checkboxes[0].scrollIntoView({ block: 'center' });
        const rect = checkboxes[0].getBoundingClientRect();
        return JSON.stringify({ action: 'click', x: Math.round(rect.x + 10), y: Math.round(rect.y + 10) });
      }
      return JSON.stringify({ action: 'already checked' });
    }
    return JSON.stringify({ action: 'not found' });
  `);
  console.log("English checkbox:", r);
  const engAction = JSON.parse(r);
  if (engAction.action === 'click') {
    await clickAt(send, engAction.x, engAction.y);
    await sleep(300);
  }

  // === SAVE ===
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
