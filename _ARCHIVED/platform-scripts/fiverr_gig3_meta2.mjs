// Fix gig #3 metadata: select English language + Industry, then save
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // === LANGUAGE ===
  console.log("=== Language ===");

  // Scroll to metadata section
  let r = await eval_(`
    const metaLabel = document.querySelector('.gig-metadata, [class*="metadata"]');
    if (metaLabel) {
      metaLabel.scrollIntoView({ block: 'start' });
      return 'scrolled to metadata';
    }
    window.scrollTo(0, 1500);
    return 'scrolled down';
  `);
  console.log(r);
  await sleep(500);

  // Find "English" in the language list - it's a clickable list item
  r = await eval_(`
    // Look for list items or labels containing "English"
    const items = Array.from(document.querySelectorAll('li, label, [class*="item"], [class*="option"]'))
      .filter(el => {
        const text = el.textContent.trim();
        return text === 'English' && el.offsetParent !== null;
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        visible: el.getBoundingClientRect().height > 0
      }));
    return JSON.stringify(items);
  `);
  console.log("English items:", r);
  const engItems = JSON.parse(r);

  if (engItems.length > 0) {
    const eng = engItems[0];
    console.log(`Clicking English at (${eng.x}, ${eng.y})`);

    // Try JS click first since CDP clicks had issues with react-select
    r = await eval_(`
      const items = Array.from(document.querySelectorAll('li, label, [class*="item"]'))
        .filter(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
      if (items.length > 0) {
        items[0].click();
        return 'clicked via JS: ' + items[0].tagName + '.' + (items[0].className?.toString() || '').substring(0, 40);
      }
      return 'not found';
    `);
    console.log("JS click:", r);
    await sleep(500);

    // Check if it worked
    r = await eval_(`
      const selected = Array.from(document.querySelectorAll('[class*="selected"], [class*="active"], [class*="checked"], input:checked'))
        .filter(el => {
          const text = (el.closest('li') || el.closest('label') || el)?.textContent?.trim() || '';
          return text.includes('English');
        })
        .map(el => ({
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 40),
          text: el.textContent.trim().substring(0, 20)
        }));
      return JSON.stringify(selected);
    `);
    console.log("English selected?", r);

    // If JS click didn't work, try CDP click
    if (r === '[]' || JSON.parse(r).length === 0) {
      console.log("JS click didn't select, trying CDP click...");
      await clickAt(send, eng.x, eng.y);
      await sleep(500);
    }
  }

  // Check language count
  r = await eval_(`
    const countText = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
    return countText ? countText[0] : 'count not found';
  `);
  console.log("Language count:", r);

  // === INDUSTRY ===
  console.log("\n=== Industry ===");

  // Click on "Industry" tab/button
  r = await eval_(`
    const industryTab = Array.from(document.querySelectorAll('li, span, button, a'))
      .filter(el => {
        const text = el.textContent.trim();
        return (text === 'Industry' || text === 'INDUSTRY') && el.offsetParent !== null;
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent.trim(),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(industryTab);
  `);
  console.log("Industry tabs:", r);
  const indTabs = JSON.parse(r);

  // Click the Industry tab (the one that's a LI with "invalid" class)
  const indTab = indTabs.find(t => t.tag === 'LI') || indTabs[0];
  if (indTab) {
    // Try JS click
    r = await eval_(`
      const tab = Array.from(document.querySelectorAll('li'))
        .find(el => el.textContent.trim() === 'Industry' || el.textContent.trim() === 'INDUSTRY');
      if (tab) {
        tab.click();
        return 'clicked Industry tab: ' + tab.className?.toString()?.substring(0, 40);
      }
      return 'not found';
    `);
    console.log("Industry tab click:", r);
    await sleep(1000);

    // Now find industry options
    r = await eval_(`
      // Look for a list of industry items
      const items = Array.from(document.querySelectorAll('li'))
        .filter(el => {
          const parent = el.closest('[class*="metadata"], [class*="list"]');
          return parent && el.offsetParent !== null && el.getBoundingClientRect().y > 0
            && el.textContent.trim().length > 2 && el.textContent.trim().length < 40
            && !el.querySelector('li');  // leaf items only
        })
        .map(el => ({
          text: el.textContent.trim(),
          class: (el.className?.toString() || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(items.slice(0, 30));
    `);
    console.log("Industry items:", r);

    // If no specific items found, look for what's visible
    const indItems = JSON.parse(r);
    if (indItems.length === 0) {
      r = await eval_(`
        // Get the visible section content
        const visibleText = document.body.innerText;
        const indIdx = visibleText.indexOf('INDUSTRY');
        if (indIdx >= 0) {
          return visibleText.substring(indIdx, indIdx + 500);
        }
        return 'INDUSTRY not found in text';
      `);
      console.log("Industry section text:", r);

      // Try broader search for any clickable items in the metadata area
      r = await eval_(`
        const allItems = Array.from(document.querySelectorAll('[class*="metadata-names"] li, [class*="metadata"] li'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            class: (el.className?.toString() || '').substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(allItems.slice(0, 20));
      `);
      console.log("All metadata items:", r);
    }

    // Select "Business & Finance" or similar industry
    const bizItem = indItems.find(i =>
      i.text.includes('Business') || i.text.includes('Career') || i.text.includes('Human') || i.text.includes('General')
    );
    if (bizItem) {
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('li'))
          .filter(el => el.textContent.trim() === '${bizItem.text}' && el.offsetParent !== null);
        if (items.length > 0) { items[0].click(); return 'selected: ' + items[0].textContent.trim(); }
        return 'not found';
      `);
      console.log("Selected industry:", r);
      await sleep(500);
    }
  }

  // Check metadata state
  r = await eval_(`
    const langCount = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
    const errors = Array.from(document.querySelectorAll('[class*="invalid"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 40));
    return JSON.stringify({ langCount: langCount?.[0], errors });
  `);
  console.log("Metadata state:", r);

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
    await sleep(8000);

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
