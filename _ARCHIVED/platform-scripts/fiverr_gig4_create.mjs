// Create gig #4: Article & Blog Writing
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

async function main() {
  // Navigate to create new gig
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Navigate to gig creation
  await eval_(`window.location.href = 'https://www.fiverr.com/users/weberg619/manage_gigs/new'`);
  await sleep(5000);
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard')
    });
  `);
  console.log("State:", r);

  // === TITLE ===
  console.log("=== Title ===");
  r = await eval_(`
    const titleInput = document.querySelector('.gig-title-input, textarea[class*="title"], textarea[name*="title"], textarea');
    if (titleInput) {
      titleInput.scrollIntoView({ block: 'center' });
      titleInput.focus();
      const rect = titleInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), val: titleInput.value });
    }
    return JSON.stringify({ error: 'no title input' });
  `);
  console.log("Title input:", r);
  const titlePos = JSON.parse(r);

  if (!titlePos.error) {
    await clickAt(send, titlePos.x, titlePos.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.insertText", { text: "I will write SEO optimized blog posts and articles on any topic" });
    await sleep(500);
    console.log("Title set");
  }

  // === CATEGORY ===
  console.log("\n=== Category ===");
  r = await eval_(`
    const combos = Array.from(document.querySelectorAll('[class*="category-selector__control"], [class*="combo"], .orca-combo-box'));
    return JSON.stringify(combos.filter(el => el.offsetParent !== null).map(el => ({
      text: el.textContent.trim().substring(0, 40),
      class: el.className.substring(0, 60),
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    })));
  `);
  console.log("Category combos:", r);
  const combos = JSON.parse(r);

  // Click first combo (category)
  if (combos.length > 0) {
    const catCombo = combos[0];
    await clickAt(send, catCombo.x, catCombo.y);
    await sleep(1000);

    // Find "Writing & Translation" option
    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="category-selector__option"], [class*="option"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    const opts = JSON.parse(r);
    const writingOpt = opts.find(o => o.text.includes("Writing"));
    if (writingOpt) {
      // Use JS dispatchEvent for React
      await eval_(`
        const opt = Array.from(document.querySelectorAll('[class*="category-selector__option"], [class*="option"]'))
          .find(el => el.textContent.trim().includes("Writing"));
        if (opt) {
          opt.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
          opt.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
          opt.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }
        return 'clicked Writing';
      `);
      console.log("Category: Writing & Translation");
      await sleep(1000);
    }
  }

  // === SUBCATEGORY ===
  console.log("\n=== Subcategory ===");
  r = await eval_(`
    const combos = Array.from(document.querySelectorAll('[class*="category-selector__control"]'))
      .filter(el => el.offsetParent !== null);
    return JSON.stringify(combos.map(el => ({
      text: el.textContent.trim().substring(0, 40),
      hasPlaceholder: el.querySelector('[class*="placeholder"]') !== null,
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    })));
  `);
  console.log("Subcategory combos:", r);
  const subcatCombos = JSON.parse(r);
  const subcatCombo = subcatCombos.find(c => c.hasPlaceholder);

  if (subcatCombo) {
    await clickAt(send, subcatCombo.x, subcatCombo.y);
    await sleep(1000);

    // Type to filter
    await send("Input.insertText", { text: "Article" });
    await sleep(1000);

    r = await eval_(`
      const opts = Array.from(document.querySelectorAll('[class*="category-selector__option"], [class*="option"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(opts);
    `);
    console.log("Subcategory options:", r);
    const subOpts = JSON.parse(r);

    // Find Articles & Blog Posts
    const articleOpt = subOpts.find(o => o.text.includes("Article") || o.text.includes("Blog"));
    if (articleOpt) {
      await eval_(`
        const opt = Array.from(document.querySelectorAll('[class*="category-selector__option"], [class*="option"]'))
          .find(el => el.textContent.trim().includes("Article") || el.textContent.trim().includes("Blog"));
        if (opt) {
          opt.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
          opt.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }));
          opt.dispatchEvent(new MouseEvent('click', { bubbles: true }));
        }
        return 'clicked';
      `);
      console.log("Subcategory set");
      await sleep(1000);
    }
  }

  // === TAGS ===
  console.log("\n=== Tags ===");
  const tags = ["blog writing", "article writing", "seo", "content writing", "copywriting"];
  for (const tag of tags) {
    r = await eval_(`
      const tagInput = document.querySelector('.react-tags__search-input input, input[class*="tag"]');
      if (tagInput) {
        tagInput.focus();
        const rect = tagInput.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no tag input' });
    `);
    const tagPos = JSON.parse(r);
    if (tagPos.error) { console.log("No tag input"); break; }

    await clickAt(send, tagPos.x, tagPos.y);
    await sleep(200);
    await send("Input.insertText", { text: tag });
    await sleep(1500);

    // Try clicking suggestion
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="suggestion"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim(),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(suggestions);
    `);
    const suggestions = JSON.parse(r);
    if (suggestions.length > 0) {
      await clickAt(send, suggestions[0].x, suggestions[0].y);
      console.log(`  Tag: "${suggestions[0].text}"`);
    } else {
      // Try Enter
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      console.log(`  Tag: "${tag}" (Enter)`);
    }
    await sleep(500);
  }

  // Verify tags
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());
    return JSON.stringify(tags);
  `);
  console.log("Tags:", r);

  // === METADATA ===
  console.log("\n=== Metadata ===");

  // Language - find English checkbox
  r = await eval_(`
    const langSection = Array.from(document.querySelectorAll('[class*="metadata"], [class*="section"]'))
      .find(el => el.textContent.includes('Language'));
    if (!langSection) return JSON.stringify({ error: 'no language section' });
    const items = Array.from(langSection.querySelectorAll('li, [class*="option"]'))
      .filter(el => el.textContent.includes('English'))
      .map(el => {
        const cb = el.querySelector('input[type="checkbox"]');
        return {
          text: el.textContent.trim().substring(0, 30),
          checked: cb ? cb.checked : false,
          cbX: cb ? Math.round(cb.getBoundingClientRect().x + 10) : 0,
          cbY: cb ? Math.round(cb.getBoundingClientRect().y + 10) : 0
        };
      });
    return JSON.stringify(items);
  `);
  console.log("Language:", r);
  const langItems = JSON.parse(r);
  if (Array.isArray(langItems) && langItems.length > 0 && !langItems[0].checked) {
    await clickAt(send, langItems[0].cbX, langItems[0].cbY);
    await sleep(500);
    console.log("English selected");
  }

  // Industry - click Business
  r = await eval_(`
    const sections = Array.from(document.querySelectorAll('[class*="metadata"], [class*="section"]'));
    const indSection = sections.find(el => el.textContent.includes('Industry') && !el.textContent.includes('Language'));
    if (!indSection) return JSON.stringify({ error: 'no industry section' });
    const items = Array.from(indSection.querySelectorAll('li, [class*="option"]'))
      .filter(el => el.textContent.trim().length > 0 && el.textContent.trim().length < 30)
      .map(el => ({
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(items);
  `);
  console.log("Industry:", r);
  const indItems = JSON.parse(r);
  if (Array.isArray(indItems)) {
    const biz = indItems.find(i => i.text.includes("Business"));
    if (biz) {
      await clickAt(send, biz.x, biz.y);
      await sleep(500);
      console.log("Business selected");
    }
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error) {
    await sleep(500);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(10000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 150));
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
