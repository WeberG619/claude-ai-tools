// Fill Content Type and Genre metadata tabs for gig #2
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

  // First scroll to the metadata section
  let r = await eval_(`
    const metaSection = document.querySelector('.gig-metadata-group, [class*="metadata-group"]');
    if (metaSection) {
      metaSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return 'scrolled to metadata';
    }
    return 'no metadata section';
  `);
  console.log(r);
  await sleep(800);

  // Find the metadata tab headers - Language, Content Type, Genre
  r = await eval_(`
    const tabItems = Array.from(document.querySelectorAll('.metadata-names-list li, [class*="metadata-name"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 30),
        class: (el.className?.toString() || '').substring(0, 60),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        isActive: (el.className?.toString() || '').includes('selected') || (el.className?.toString() || '').includes('active')
      }));
    return JSON.stringify(tabItems);
  `);
  console.log("Metadata tabs:", r);
  const metaTabs = JSON.parse(r);

  // Click "Content Type" tab
  const contentTab = metaTabs.find(t => t.text.includes('Content Type'));
  if (contentTab) {
    console.log(`\n=== Clicking Content Type tab at (${contentTab.x}, ${contentTab.y}) ===`);
    await clickAt(send, contentTab.x, contentTab.y);
    await sleep(1000);

    // Now check what appeared
    r = await eval_(`
      // Look for the active metadata content panel
      const panel = document.querySelector('.metadata-content.active, .metadata-content:not(.hidden), [class*="metadata-content"]');

      // Check for checkboxes in the metadata area
      const metaGroup = document.querySelector('.gig-metadata-group');
      const checkboxes = metaGroup ? Array.from(metaGroup.querySelectorAll('label'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 800 && rect.height > 0;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          checked: el.querySelector('input')?.checked || false
        })) : [];

      // Also check for dropdowns/selects
      const combos = metaGroup ? Array.from(metaGroup.querySelectorAll('.orca-combo-box-container'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: (el.querySelector('[class*="singleValue"]')?.textContent?.trim() || el.querySelector('[class*="placeholder"]')?.textContent?.trim() || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          class: (el.className?.toString() || '').substring(0, 60)
        })) : [];

      return JSON.stringify({ checkboxes: checkboxes.slice(0, 20), combos });
    `);
    console.log("Content Type panel:", r);
    const ctPanel = JSON.parse(r);

    if (ctPanel.checkboxes.length > 0) {
      console.log("Content type options:", ctPanel.checkboxes.map(c => c.text).join(', '));
      // Select relevant content types for proofreading
      const targets = ['Article', 'Blog', 'Book', 'Web', 'Academic', 'Business', 'Email', 'Resume', 'Other', 'General'];
      for (const cb of ctPanel.checkboxes) {
        if (!cb.checked && targets.some(t => cb.text.includes(t))) {
          console.log(`  Selecting: "${cb.text}"`);
          await clickAt(send, cb.x, cb.y);
          await sleep(200);
        }
      }
    } else if (ctPanel.combos.length > 0) {
      console.log("Content type dropdowns:", ctPanel.combos);
      // Click first dropdown
      const combo = ctPanel.combos[0];
      await clickAt(send, combo.x, combo.y);
      await sleep(1000);

      r = await eval_(`
        const menu = document.querySelector('[class*="menu-list"], [class*="menuList"]');
        if (menu) {
          return JSON.stringify(Array.from(menu.children).map(el => ({
            text: el.textContent.trim().substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          })).slice(0, 15));
        }
        return '[]';
      `);
      console.log("Dropdown options:", r);
      const options = JSON.parse(r);
      // Select first relevant option
      const target = options.find(o => o.text.includes('Article') || o.text.includes('Blog') || o.text.includes('General') || o.text.includes('Book')) || options[0];
      if (target) {
        console.log(`  Selecting: "${target.text}"`);
        await clickAt(send, target.x, target.y);
        await sleep(500);
      }
    }
  }

  // Click "Genre" tab
  const genreTab = metaTabs.find(t => t.text.includes('Genre'));
  if (genreTab) {
    console.log(`\n=== Clicking Genre tab at (${genreTab.x}, ${genreTab.y}) ===`);
    await clickAt(send, genreTab.x, genreTab.y);
    await sleep(1000);

    r = await eval_(`
      const metaGroup = document.querySelector('.gig-metadata-group');
      const checkboxes = metaGroup ? Array.from(metaGroup.querySelectorAll('label'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 800 && rect.height > 0;
        })
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + 10),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
          checked: el.querySelector('input')?.checked || false
        })) : [];

      const combos = metaGroup ? Array.from(metaGroup.querySelectorAll('.orca-combo-box-container'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          text: (el.querySelector('[class*="singleValue"]')?.textContent?.trim() || el.querySelector('[class*="placeholder"]')?.textContent?.trim() || '').substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        })) : [];

      return JSON.stringify({ checkboxes: checkboxes.slice(0, 20), combos });
    `);
    console.log("Genre panel:", r);
    const genrePanel = JSON.parse(r);

    if (genrePanel.checkboxes.length > 0) {
      console.log("Genre options:", genrePanel.checkboxes.map(c => c.text).join(', '));
      const targets = ['Non-fiction', 'Business', 'Technical', 'Academic', 'Science', 'General', 'Other'];
      for (const cb of genrePanel.checkboxes) {
        if (!cb.checked && targets.some(t => cb.text.includes(t))) {
          console.log(`  Selecting: "${cb.text}"`);
          await clickAt(send, cb.x, cb.y);
          await sleep(200);
        }
      }
    } else if (genrePanel.combos.length > 0) {
      const combo = genrePanel.combos[0];
      await clickAt(send, combo.x, combo.y);
      await sleep(1000);

      r = await eval_(`
        const menu = document.querySelector('[class*="menu-list"], [class*="menuList"]');
        if (menu) {
          return JSON.stringify(Array.from(menu.children).map(el => ({
            text: el.textContent.trim().substring(0, 60),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          })).slice(0, 15));
        }
        return '[]';
      `);
      const options = JSON.parse(r);
      const target = options.find(o => o.text.includes('Non-fiction') || o.text.includes('Business') || o.text.includes('General')) || options[0];
      if (target) {
        console.log(`  Selecting: "${target.text}"`);
        await clickAt(send, target.x, target.y);
        await sleep(500);
      }
    }
  }

  // Check errors
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\n=== Errors after metadata fix ===");
  console.log(r);
  const errors = JSON.parse(r);

  // Try Save & Continue
  if (!errors.some(e => e.includes('metadata') || e.includes('I will') || e.includes('service type'))) {
    console.log("\nScrolling to Save & Continue...");
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
      console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
      await clickAt(send, saveBtn.x, saveBtn.y);
      await sleep(5000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          errors: Array.from(document.querySelectorAll('[class*="error"]'))
            .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
            .map(el => el.textContent.trim().substring(0, 100)),
          body: (document.body?.innerText || '').substring(0, 500)
        });
      `);
      console.log("After save:", r);
    }
  } else {
    console.log("\nStill have blocking errors, not saving.");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
