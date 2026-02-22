// Create Fiverr Gig #3: Resume & CV Writing - Full flow from start
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab with "${urlMatch}" not found. Tabs: ${tabs.map(t=>t.url).join(', ')}`);
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

async function clickSave(send, eval_) {
  let r = await eval_(`
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
  const btn = JSON.parse(r);
  if (!btn.error) {
    await clickAt(send, btn.x, btn.y);
    await sleep(5000);
    r = await eval_(`return JSON.stringify({ wizard: new URL(location.href).searchParams.get('wizard'), url: location.href })`);
    return JSON.parse(r);
  }
  return null;
}

async function main() {
  // Step 1: Navigate to create new gig
  console.log("=== Step 1: Navigate to Create New Gig ===");
  let { ws, send, eval_ } = await connectToPage("fiverr.com");

  await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs" });
  await sleep(5000);

  // Close old websocket and reconnect to the new page
  ws.close();
  await sleep(1000);

  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

  // Click "Create a New Gig"
  let r = await eval_(`
    const createBtn = Array.from(document.querySelectorAll('a, button'))
      .find(el => el.textContent.trim().includes('Create a New Gig'));
    if (createBtn) {
      const rect = createBtn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), href: createBtn.href || '' });
    }
    return JSON.stringify({ error: 'no create button', body: (document.body?.innerText || '').substring(0, 500) });
  `);
  console.log("Create button:", r);
  const createBtn = JSON.parse(r);

  if (createBtn.href) {
    await send("Page.navigate", { url: createBtn.href });
  } else if (!createBtn.error) {
    await clickAt(send, createBtn.x, createBtn.y);
  } else {
    console.log("Trying direct URL...");
    await send("Page.navigate", { url: "https://www.fiverr.com/users/weberg619/manage_gigs/new" });
  }
  await sleep(5000);

  // Reconnect
  ws.close();
  await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("manage_gigs"));

  r = await eval_(`return location.href`);
  console.log("URL:", r);

  // === OVERVIEW STEP ===
  console.log("\n=== Step 2: Overview ===");

  // Title
  r = await eval_(`
    const titleInput = document.querySelector('.gig-title-input textarea, textarea[class*="title"]');
    if (titleInput) {
      const rect = titleInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no title input' });
  `);
  console.log("Title input:", r);
  const titleInput = JSON.parse(r);

  if (!titleInput.error) {
    await tripleClick(send, titleInput.x, titleInput.y);
    await sleep(200);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);
    await send("Input.insertText", { text: "write a professional resume, CV, and cover letter for your job search" });
    await sleep(500);
    console.log("Title filled");
  }

  // Category: Writing & Translation
  r = await eval_(`
    const control = document.querySelector('[class*="category-selector__control"], .orca-combo-box [class*="control"]');
    if (control) {
      control.scrollIntoView({ block: 'center' });
      const rect = control.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no category control' });
  `);
  console.log("Category control:", r);
  const catControl = JSON.parse(r);

  if (!catControl.error) {
    await sleep(300);
    await clickAt(send, catControl.x, catControl.y);
    await sleep(1000);

    // Click "Writing & Translation"
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[class*="menu-list"] > div, [class*="option"]'))
        .filter(el => el.textContent.trim().includes('Writing') && el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    console.log("Category options:", r);
    const catOptions = JSON.parse(r);
    const writingOpt = catOptions.find(o => o.text.includes('Writing'));
    if (writingOpt) {
      await clickAt(send, writingOpt.x, writingOpt.y);
      await sleep(1000);
      console.log("Selected Writing & Translation");
    }
  }

  // Subcategory - should auto-populate, but we want "Resume Writing"
  await sleep(1000);
  r = await eval_(`
    const subControl = document.querySelectorAll('[class*="control"]');
    const allCombos = Array.from(document.querySelectorAll('.orca-combo-box'));
    // The second combo box is the subcategory
    if (allCombos.length >= 2) {
      const sub = allCombos[1].querySelector('[class*="control"]');
      if (sub) {
        const rect = sub.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: sub.textContent.trim().substring(0, 30) });
      }
    }
    return JSON.stringify({ error: 'no subcategory' });
  `);
  console.log("Subcategory:", r);
  const subControl = JSON.parse(r);

  if (!subControl.error) {
    await clickAt(send, subControl.x, subControl.y);
    await sleep(1000);

    // Find "Resume Writing" option
    r = await eval_(`
      const options = Array.from(document.querySelectorAll('[class*="menu-list"] > div, [class*="option"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(options);
    `);
    console.log("Subcategory options:", r);
    const subOptions = JSON.parse(r);
    const resumeOpt = subOptions.find(o => o.text.includes('Resume'));
    if (resumeOpt) {
      await clickAt(send, resumeOpt.x, resumeOpt.y);
      await sleep(1000);
      console.log("Selected Resume Writing");
    }
  }

  // Service Type dropdown
  await sleep(500);
  r = await eval_(`
    const serviceType = document.querySelector('.gig-service-type-wrapper select, .gig-service-type-wrapper [class*="control"]');
    if (serviceType) {
      serviceType.scrollIntoView({ block: 'center' });
      const rect = serviceType.getBoundingClientRect();
      return JSON.stringify({ tag: serviceType.tagName, x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    // Try finding the service type section differently
    const serviceSection = Array.from(document.querySelectorAll('[class*="service-type"], select'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify({ options: serviceSection });
  `);
  console.log("Service type:", r);

  // Tags
  console.log("\n--- Tags ---");
  r = await eval_(`
    const tagInput = document.querySelector('.react-tags__search-input input, [class*="tag"] input');
    if (tagInput) {
      tagInput.scrollIntoView({ block: 'center' });
      const rect = tagInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no tag input' });
  `);
  const tagInput = JSON.parse(r);

  if (!tagInput.error) {
    const tags = ["resume writing", "cv writing", "cover letter", "linkedin profile", "career"];
    for (const tag of tags) {
      await clickAt(send, tagInput.x, tagInput.y);
      await sleep(300);
      await send("Input.insertText", { text: tag });
      await sleep(800);

      // Try to click suggestion or press Enter
      r = await eval_(`
        const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="suggestion"] li'))
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
      } else {
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
      }
      await sleep(500);
    }
    console.log("Tags added");
  }

  // Metadata - Language (English)
  console.log("\n--- Metadata ---");
  r = await eval_(`
    const langCheckbox = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .find(el => {
        const label = (el.closest('label') || el.parentElement)?.textContent?.trim() || '';
        return label.includes('English') && el.offsetParent !== null;
      });
    if (langCheckbox) {
      if (!langCheckbox.checked) {
        langCheckbox.scrollIntoView({ block: 'center' });
        const rect = langCheckbox.getBoundingClientRect();
        return JSON.stringify({ checked: false, x: Math.round(rect.x + 10), y: Math.round(rect.y + 10) });
      }
      return JSON.stringify({ checked: true });
    }
    return JSON.stringify({ error: 'no english checkbox' });
  `);
  console.log("English checkbox:", r);
  const engCb = JSON.parse(r);
  if (!engCb.error && !engCb.checked) {
    await clickAt(send, engCb.x, engCb.y);
    await sleep(300);
  }

  // Try to save overview
  console.log("\n--- Save Overview ---");
  let result = await clickSave(send, eval_);
  console.log("After overview save:", JSON.stringify(result));

  // Check for errors and handle them
  if (result && result.wizard === '0' || !result) {
    // Still on overview - check errors
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify(errors);
    `);
    console.log("Errors:", r);
  }

  // If wizard advanced, report and exit (we'll handle subsequent steps in next script)
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 800)
    });
  `);
  console.log("\nFinal state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
