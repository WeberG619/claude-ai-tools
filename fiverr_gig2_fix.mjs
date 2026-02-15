// Fix gig #2 validation errors: title, service type, metadata
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

  // Scroll to top first
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Fix 1: Title - remove "I will" prefix since Fiverr adds it
  console.log("=== Fix 1: Title ===");
  let r = await eval_(`
    const textarea = document.querySelector('textarea[name="gig[title]"], .gig-title-textarea, textarea');
    if (textarea) {
      const rect = textarea.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        value: textarea.value
      });
    }
    // Try input field
    const input = document.querySelector('input.gig-title-input, input[class*="title"]');
    if (input) {
      const rect = input.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        value: input.value,
        type: 'input'
      });
    }
    return JSON.stringify({ error: 'no title field' });
  `);
  console.log("Title field:", r);
  const titleField = JSON.parse(r);

  if (!titleField.error) {
    await clickAt(send, titleField.x, titleField.y);
    await sleep(300);
    // Select all and replace
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    // New title without "I will" - Fiverr adds "I will" as a prefix
    await send("Input.insertText", { text: "do professional proofreading, editing, and rewriting of your content" });
    await sleep(500);

    // Verify
    r = await eval_(`
      const h = document.querySelector('input[name="gig[title]"]');
      const errors = Array.from(document.querySelectorAll('.title-status-msg'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim());
      return JSON.stringify({ hiddenValue: h?.value || '', errors });
    `);
    console.log("Title after fix:", r);
  }

  // Fix 2: Service Type dropdown
  console.log("\n=== Fix 2: Service Type ===");
  r = await eval_(`
    const stWrapper = document.querySelector('.gig-service-type-wrapper');
    if (!stWrapper) return JSON.stringify({ error: 'no service type wrapper' });
    const control = stWrapper.querySelector('[class*="control"]');
    if (control) {
      const rect = control.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        currentValue: stWrapper.querySelector('[class*="singleValue"]')?.textContent?.trim() || 'empty'
      });
    }
    return JSON.stringify({ error: 'no control' });
  `);
  console.log("Service type dropdown:", r);
  const stCtrl = JSON.parse(r);

  if (!stCtrl.error) {
    await clickAt(send, stCtrl.x, stCtrl.y);
    await sleep(1000);

    // Get options
    r = await eval_(`
      const menu = document.querySelector('[class*="menu-list"], [class*="menuList"]');
      if (menu) {
        return JSON.stringify(Array.from(menu.children).map(el => ({
          text: el.textContent.trim().substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        })));
      }
      return '[]';
    `);
    console.log("Service type options:", r);
    const stOpts = JSON.parse(r);

    if (stOpts.length > 0) {
      // Look for Proofreading or Editing related option
      const proof = stOpts.find(o => o.text.includes('Proofreading')) ||
                    stOpts.find(o => o.text.includes('Editing')) ||
                    stOpts.find(o => o.text.includes('Copy')) ||
                    stOpts[0];
      console.log(`Selecting: "${proof.text}"`);
      await clickAt(send, proof.x, proof.y);
      await sleep(2000);
    }
  }

  // Fix 3: Metadata - Language and Content Type
  console.log("\n=== Fix 3: Metadata - Language ===");
  // Language is a checkbox list - need to select English
  r = await eval_(`
    const englishLabel = Array.from(document.querySelectorAll('label'))
      .find(l => l.textContent.trim() === 'English' && l.getBoundingClientRect().y > 800 && l.getBoundingClientRect().y < 2200);
    if (englishLabel) {
      const checkbox = englishLabel.querySelector('input[type="checkbox"]') || englishLabel.previousElementSibling;
      const rect = englishLabel.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + 10),
        y: Math.round(rect.y + rect.height/2),
        checked: checkbox?.checked || false,
        checkboxId: checkbox?.id || ''
      });
    }
    return JSON.stringify({ error: 'no English label' });
  `);
  console.log("English checkbox:", r);
  const engCb = JSON.parse(r);

  if (!engCb.error && !engCb.checked) {
    // Scroll to it first
    await eval_(`
      const el = Array.from(document.querySelectorAll('label'))
        .find(l => l.textContent.trim() === 'English' && l.getBoundingClientRect().y > 800);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    `);
    await sleep(500);

    // Re-get position after scroll
    r = await eval_(`
      const englishLabel = Array.from(document.querySelectorAll('label'))
        .find(l => l.textContent.trim() === 'English' && l.closest('[class*="language"], [class*="metadata"]'));
      if (englishLabel) {
        const rect = englishLabel.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'not found after scroll' });
    `);
    console.log("English after scroll:", r);
    const engPos = JSON.parse(r);
    if (!engPos.error) {
      await clickAt(send, engPos.x, engPos.y);
      await sleep(500);
      console.log("Clicked English");
    }
  }

  // Content Type metadata
  console.log("\n=== Fix 3b: Metadata - Content Type ===");
  r = await eval_(`
    // Find the content type section
    const contentTypeHeader = Array.from(document.querySelectorAll('*'))
      .find(el => el.textContent.trim() === 'Content type' || el.textContent.trim() === 'CONTENT TYPE');

    if (contentTypeHeader) {
      // Find nearby checkboxes or dropdowns
      const parent = contentTypeHeader.closest('[class*="metadata"]') || contentTypeHeader.parentElement?.parentElement;
      if (parent) {
        const labels = Array.from(parent.querySelectorAll('label'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify({ labels });
      }
    }

    // Alternative: look for content type dropdown
    const ctDropdown = document.querySelector('[class*="content-type"] [class*="control"], [class*="contentType"]');
    if (ctDropdown) {
      const rect = ctDropdown.getBoundingClientRect();
      return JSON.stringify({ dropdown: { x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) }});
    }

    return JSON.stringify({ error: 'no content type section found' });
  `);
  console.log("Content type section:", r);
  const ctSection = JSON.parse(r);

  if (ctSection.labels && ctSection.labels.length > 0) {
    // It's a checkbox list - look for relevant options like "Articles & Blog Posts" or similar
    console.log("Content type options:", ctSection.labels.map(l => l.text).join(', '));

    // Scroll to content type area
    await eval_(`
      const ct = Array.from(document.querySelectorAll('*'))
        .find(el => el.textContent.trim() === 'CONTENT TYPE' || el.textContent.trim() === 'Content type');
      if (ct) ct.scrollIntoView({ behavior: 'smooth', block: 'center' });
    `);
    await sleep(500);

    // Re-get positions after scroll
    r = await eval_(`
      const contentTypeHeader = Array.from(document.querySelectorAll('*'))
        .find(el => (el.textContent.trim() === 'Content type' || el.textContent.trim() === 'CONTENT TYPE') && el.children.length === 0);
      if (!contentTypeHeader) return JSON.stringify({ error: 'no header' });

      // Go up to find the metadata group container
      let container = contentTypeHeader;
      for (let i = 0; i < 5; i++) {
        container = container.parentElement;
        if (!container) break;
        const labels = Array.from(container.querySelectorAll('label'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0);
        if (labels.length > 3) {
          return JSON.stringify(labels.map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          })));
        }
      }
      return JSON.stringify({ error: 'no labels in container' });
    `);
    console.log("Content type labels after scroll:", r);
    const ctLabels = JSON.parse(r);

    if (Array.isArray(ctLabels)) {
      // Select relevant ones: articles, blog posts, books, web content, etc.
      const targets = ['Articles', 'Blog', 'Book', 'Web', 'Academic', 'Other'];
      for (const label of ctLabels) {
        if (targets.some(t => label.text.includes(t))) {
          console.log(`Selecting: "${label.text}"`);
          await clickAt(send, label.x, label.y);
          await sleep(300);
        }
      }
    }
  } else if (ctSection.dropdown) {
    // It's a dropdown
    await clickAt(send, ctSection.dropdown.x, ctSection.dropdown.y);
    await sleep(1000);
    // Select first option
    r = await eval_(`
      const menu = document.querySelector('[class*="menu-list"]');
      if (menu && menu.children.length > 0) {
        const first = menu.children[0];
        const rect = first.getBoundingClientRect();
        return JSON.stringify({ text: first.textContent.trim(), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no menu' });
    `);
    if (!JSON.parse(r).error) {
      const opt = JSON.parse(r);
      await clickAt(send, opt.x, opt.y);
      await sleep(500);
    }
  }

  // Check for remaining errors
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\n=== Remaining errors ===");
  console.log(r);

  // Final state
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      serviceType: document.querySelector('.gig-service-type-wrapper [class*="singleValue"]')?.textContent?.trim() || ''
    });
  `);
  console.log("\n=== Final State ===");
  console.log(r);

  // Scroll to Save & Continue
  await eval_(`window.scrollTo(0, document.body.scrollHeight)`);
  await sleep(500);

  // Find and click Save & Continue
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue' && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      await new Promise(r => setTimeout(r, 500));
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  console.log("\nSave button:", r);
  const saveBtn = JSON.parse(r);
  if (!saveBtn.error && !saveBtn.disabled) {
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 100)),
        body: (document.body?.innerText || '').substring(0, 500)
      });
    `);
    console.log("After save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
