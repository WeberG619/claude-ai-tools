// Fix gig #3 metadata using CDP clicks (not JS .click())
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

  // Scroll to metadata section
  let r = await eval_(`
    const metaLabel = document.querySelector('[class*="metadata-names"]');
    if (metaLabel) {
      metaLabel.scrollIntoView({ block: 'start' });
      return 'scrolled to metadata';
    }
    // Try text-based search
    const allEls = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent.trim() === 'Gig metadata' && el.children.length < 3);
    if (allEls) { allEls.scrollIntoView({ block: 'start' }); return 'scrolled to Gig metadata'; }
    window.scrollTo(0, 1500);
    return 'scrolled down';
  `);
  console.log(r);
  await sleep(500);

  // === LANGUAGE: Click "English" using CDP mouse events ===
  console.log("\n=== Language ===");

  // First ensure Language tab is selected
  r = await eval_(`
    const langTab = Array.from(document.querySelectorAll('li'))
      .find(el => el.textContent.trim() === 'Language' && el.className?.includes?.('invalid'));
    if (langTab && !langTab.className.includes('selected')) {
      langTab.scrollIntoView({ block: 'center' });
      const rect = langTab.getBoundingClientRect();
      return JSON.stringify({ action: 'click_tab', x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ action: 'already_selected' });
  `);
  console.log("Language tab:", r);
  const langTab = JSON.parse(r);
  if (langTab.action === 'click_tab') {
    await clickAt(send, langTab.x, langTab.y);
    await sleep(500);
  }

  // Find English in the options list
  r = await eval_(`
    const eng = Array.from(document.querySelectorAll('li.option, [class*="option"]'))
      .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
    if (eng) {
      eng.scrollIntoView({ block: 'center' });
      const rect = eng.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), text: eng.textContent.trim() });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("English option:", r);
  const engOpt = JSON.parse(r);

  if (!engOpt.error) {
    console.log(`CDP clicking English at (${engOpt.x}, ${engOpt.y})`);
    await clickAt(send, engOpt.x, engOpt.y);
    await sleep(1000);

    // Verify
    r = await eval_(`
      const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
      const selectedItems = Array.from(document.querySelectorAll('[class*="selected"]'))
        .filter(el => el.textContent?.trim() === 'English')
        .map(el => el.className?.toString()?.substring(0, 40));
      return JSON.stringify({ count: countMatch?.[0], selectedItems });
    `);
    console.log("After English click:", r);

    // If still 0/3, try clicking the inner element (label or checkbox)
    const result = JSON.parse(r);
    if (result.count === '0 / 3') {
      console.log("Still 0/3, trying inner elements...");

      // Try clicking the checkbox/input inside English
      r = await eval_(`
        const eng = Array.from(document.querySelectorAll('li.option'))
          .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
        if (eng) {
          // Check inner structure
          const inner = eng.innerHTML.substring(0, 200);
          // Find any clickable child
          const checkbox = eng.querySelector('input[type="checkbox"]');
          const label = eng.querySelector('label');
          const div = eng.querySelector('div');
          return JSON.stringify({
            inner,
            hasCheckbox: !!checkbox,
            hasLabel: !!label,
            hasDiv: !!div,
            childTags: Array.from(eng.children).map(c => c.tagName + '.' + (c.className?.toString() || '').substring(0, 30))
          });
        }
        return JSON.stringify({ error: 'not found' });
      `);
      console.log("English inner structure:", r);

      // Try dispatching mouseDown event via React's synthetic event system
      r = await eval_(`
        const eng = Array.from(document.querySelectorAll('li.option'))
          .find(el => el.textContent.trim() === 'English' && el.offsetParent !== null);
        if (eng) {
          // Dispatch full sequence of mouse events with bubbles
          const opts = { bubbles: true, cancelable: true, view: window };
          eng.dispatchEvent(new MouseEvent('mouseenter', opts));
          eng.dispatchEvent(new MouseEvent('mouseover', opts));
          eng.dispatchEvent(new MouseEvent('mousedown', opts));
          eng.dispatchEvent(new MouseEvent('mouseup', opts));
          eng.dispatchEvent(new MouseEvent('click', opts));
          return 'dispatched full event sequence';
        }
        return 'not found';
      `);
      console.log("Full event dispatch:", r);
      await sleep(1000);

      r = await eval_(`
        const countMatch = document.body.innerText.match(/(\\d+)\\s*\\/\\s*3/);
        return countMatch?.[0] || 'count not found';
      `);
      console.log("Count after full dispatch:", r);
    }
  }

  // === INDUSTRY ===
  console.log("\n=== Industry ===");

  // Click Industry tab using CDP
  r = await eval_(`
    const indTab = Array.from(document.querySelectorAll('li'))
      .find(el => (el.textContent.trim() === 'Industry' || el.textContent.trim() === 'INDUSTRY')
        && el.className?.includes?.('invalid'));
    if (indTab) {
      indTab.scrollIntoView({ block: 'center' });
      const rect = indTab.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  console.log("Industry tab:", r);
  const indTabPos = JSON.parse(r);

  if (!indTabPos.error) {
    await clickAt(send, indTabPos.x, indTabPos.y);
    await sleep(1000);

    // Find "Business" industry option
    r = await eval_(`
      const biz = Array.from(document.querySelectorAll('li.option'))
        .find(el => el.textContent.trim() === 'Business' && el.offsetParent !== null);
      if (biz) {
        biz.scrollIntoView({ block: 'center' });
        const rect = biz.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    console.log("Business option:", r);
    const bizOpt = JSON.parse(r);

    if (!bizOpt.error) {
      console.log(`CDP clicking Business at (${bizOpt.x}, ${bizOpt.y})`);
      await clickAt(send, bizOpt.x, bizOpt.y);
      await sleep(1000);
    }

    // Also select "General"
    r = await eval_(`
      const gen = Array.from(document.querySelectorAll('li.option'))
        .find(el => el.textContent.trim() === 'General' && el.offsetParent !== null);
      if (gen) {
        gen.scrollIntoView({ block: 'center' });
        const rect = gen.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found' });
    `);
    console.log("General option:", r);
    const genOpt = JSON.parse(r);

    if (!genOpt.error) {
      await clickAt(send, genOpt.x, genOpt.y);
      await sleep(500);
    }
  }

  // Check metadata state
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="invalid"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify({ errors });
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
