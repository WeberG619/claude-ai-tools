// Fix remaining issues: title, content type, genre metadata
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

  // Scroll to top
  await eval_(`window.scrollTo(0, 0)`);
  await sleep(500);

  // Fix 1: Title - use triple-click to select all, then type new text
  console.log("=== Fix 1: Title ===");
  let r = await eval_(`
    const textarea = document.querySelector('textarea');
    if (textarea) {
      textarea.scrollIntoView({ block: 'center' });
      const rect = textarea.getBoundingClientRect();
      return JSON.stringify({
        x: Math.round(rect.x + rect.width/2),
        y: Math.round(rect.y + rect.height/2),
        value: textarea.value
      });
    }
    return JSON.stringify({ error: 'no textarea' });
  `);
  console.log("Textarea:", r);
  const ta = JSON.parse(r);

  if (!ta.error) {
    // Triple click to select all text in textarea
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: ta.x, y: ta.y, button: "left", clickCount: 1 });
    await sleep(30);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ta.x, y: ta.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: ta.x, y: ta.y, button: "left", clickCount: 2 });
    await sleep(30);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ta.x, y: ta.y, button: "left", clickCount: 2 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: ta.x, y: ta.y, button: "left", clickCount: 3 });
    await sleep(30);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: ta.x, y: ta.y, button: "left", clickCount: 3 });
    await sleep(200);

    // Now type the replacement - no "I will" prefix
    await send("Input.insertText", { text: "do professional proofreading, editing, and rewriting of your content" });
    await sleep(500);

    // Verify
    r = await eval_(`
      const h = document.querySelector('input[name="gig[title]"]');
      const ta = document.querySelector('textarea');
      return JSON.stringify({
        hiddenValue: h?.value || '',
        textareaValue: ta?.value || ''
      });
    `);
    console.log("Title after fix:", r);

    // Check if still has error
    r = await eval_(`
      const err = document.querySelector('.title-status-msg');
      return err?.offsetParent ? err.textContent.trim() : 'no error';
    `);
    console.log("Title error:", r);

    // If triple-click didn't work, try JS approach
    if (r !== 'no error' && r.includes('I will')) {
      console.log("Triple-click didn't fully clear. Using JS to set value...");
      r = await eval_(`
        const ta = document.querySelector('textarea');
        if (ta) {
          // Set via React's native value setter to trigger React state update
          const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          nativeSetter.call(ta, 'do professional proofreading, editing, and rewriting of your content');
          ta.dispatchEvent(new Event('input', { bubbles: true }));
          ta.dispatchEvent(new Event('change', { bubbles: true }));
          return ta.value;
        }
        return 'no textarea';
      `);
      console.log("JS set result:", r);
      await sleep(500);

      r = await eval_(`return document.querySelector('input[name="gig[title]"]')?.value || ''`);
      console.log("Hidden title value:", r);
    }
  }

  // Fix 2: Content Type and Genre metadata
  console.log("\n=== Fix 2: Content Type & Genre Metadata ===");

  // Find all metadata sections
  r = await eval_(`
    // Get all metadata group containers
    const metaGroups = Array.from(document.querySelectorAll('[class*="metadata"], [class*="meta-group"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 200) || '',
        y: Math.round(el.getBoundingClientRect().y),
        childLabels: Array.from(el.querySelectorAll('label')).slice(0, 5).map(l => l.textContent.trim().substring(0, 30))
      }));

    // Also find all checkbox groups with their headers
    const headers = ['Content type', 'CONTENT TYPE', 'Genre', 'GENRE'];
    const sections = [];
    for (const h of headers) {
      const headerEl = Array.from(document.querySelectorAll('*'))
        .find(el => el.children.length === 0 && el.textContent.trim().toLowerCase() === h.toLowerCase());
      if (headerEl) {
        // Walk up to find the section container
        let container = headerEl.parentElement;
        for (let i = 0; i < 3; i++) {
          if (!container) break;
          const checkboxes = container.querySelectorAll('input[type="checkbox"], label');
          if (checkboxes.length > 2) {
            const labels = Array.from(container.querySelectorAll('label'))
              .map(l => ({
                text: l.textContent.trim().substring(0, 40),
                y: Math.round(l.getBoundingClientRect().y),
                checked: l.querySelector('input[type="checkbox"]')?.checked || false
              }));
            sections.push({ header: h, labelCount: labels.length, labels: labels.slice(0, 20) });
            break;
          }
          container = container.parentElement;
        }
      }
    }

    return JSON.stringify({ metaGroups: metaGroups.slice(0, 5), sections });
  `);
  console.log("Metadata sections:", r);
  const metaData = JSON.parse(r);

  // Handle Content Type section
  for (const section of metaData.sections) {
    console.log(`\n--- ${section.header} (${section.labelCount} options) ---`);
    console.log("Options:", section.labels.map(l => `${l.text}${l.checked ? ' [x]' : ''}`).join(', '));

    // Scroll to section and select relevant options
    await eval_(`
      const headerEl = Array.from(document.querySelectorAll('*'))
        .find(el => el.children.length === 0 && el.textContent.trim().toLowerCase() === '${section.header.toLowerCase()}');
      if (headerEl) headerEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
    `);
    await sleep(600);

    // Select relevant options based on section type
    let targetTexts = [];
    if (section.header.toLowerCase().includes('content')) {
      // For content type: articles, blog posts, web content, books
      targetTexts = ['Article', 'Blog', 'Book', 'Web', 'Email', 'Academic'];
    } else if (section.header.toLowerCase().includes('genre')) {
      // For genre: general/all
      targetTexts = ['Non-fiction', 'Business', 'Technical', 'Academic', 'Other'];
    }

    for (const label of section.labels) {
      if (label.checked) continue;
      if (targetTexts.some(t => label.text.includes(t))) {
        // Get fresh position after scroll
        r = await eval_(`
          const label = Array.from(document.querySelectorAll('label'))
            .find(l => l.textContent.trim() === '${label.text}' && l.getBoundingClientRect().y > 0);
          if (label) {
            const rect = label.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + 10), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'not found' });
        `);
        const pos = JSON.parse(r);
        if (!pos.error) {
          console.log(`  Selecting: "${label.text}"`);
          await clickAt(send, pos.x, pos.y);
          await sleep(300);
        }
      }
    }
  }

  // If no sections found, try a different approach - look for combo boxes
  if (metaData.sections.length === 0) {
    console.log("No checkbox sections found. Looking for other metadata inputs...");
    r = await eval_(`
      const allCombos = Array.from(document.querySelectorAll('.orca-combo-box-container'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          class: (el.className?.toString() || '').substring(0, 80),
          text: el.textContent?.trim()?.substring(0, 60) || '',
          y: Math.round(el.getBoundingClientRect().y)
        }));
      return JSON.stringify(allCombos);
    `);
    console.log("All combo boxes:", r);
  }

  // Check remaining errors
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\n=== Remaining errors ===");
  console.log(r);
  const remainingErrors = JSON.parse(r);

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

  // Try Save & Continue if no blocking errors
  if (remainingErrors.length === 0 || !remainingErrors.some(e => e.includes('I will') || e.includes('metadata') || e.includes('service type'))) {
    console.log("\nAttempting Save & Continue...");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (btn) {
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return 'scrolling';
      }
      return 'no button';
    `);
    await sleep(800);

    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), disabled: btn.disabled });
      }
      return JSON.stringify({ error: 'no button' });
    `);
    const saveBtn = JSON.parse(r);
    if (!saveBtn.error) {
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
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
