// Click Genre tab, fill it, then Save & Continue
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

  // Scroll metadata section into view
  await eval_(`
    const metaSection = document.querySelector('.gig-metadata-group');
    if (metaSection) metaSection.scrollIntoView({ behavior: 'instant', block: 'start' });
  `);
  await sleep(500);

  // Click Genre tab
  let r = await eval_(`
    const genreTab = Array.from(document.querySelectorAll('.metadata-names-list li'))
      .find(li => li.textContent.trim() === 'Genre');
    if (genreTab) {
      const rect = genreTab.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no genre tab' });
  `);
  console.log("Genre tab position:", r);
  const genrePos = JSON.parse(r);

  if (!genrePos.error) {
    console.log(`Clicking Genre tab at (${genrePos.x}, ${genrePos.y})`);
    await clickAt(send, genrePos.x, genrePos.y);
    await sleep(1000);

    // Get genre options
    r = await eval_(`
      const metaOpts = document.querySelector('.metadata-options');
      if (metaOpts) {
        const labels = Array.from(metaOpts.querySelectorAll('label'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
            checked: el.querySelector('input')?.checked || false
          }));
        const desc = metaOpts.querySelector('p, [class*="description"]')?.textContent?.trim()?.substring(0, 100) || '';
        const limit = metaOpts.querySelector('[class*="count"], [class*="limit"]')?.textContent?.trim() || '';
        return JSON.stringify({ labels, desc, limit });
      }
      return JSON.stringify({ error: 'no options panel' });
    `);
    console.log("Genre options:", r);
    const genreOpts = JSON.parse(r);

    if (genreOpts.labels) {
      console.log("Available genres:", genreOpts.labels.map(l => l.text).join(', '));
      console.log("Limit:", genreOpts.limit);

      // Select relevant genres for proofreading service
      const targets = ['Non-fiction', 'Business', 'Technical', 'Academic', 'Science', 'Self-help', 'General', 'Other'];
      let selected = 0;
      for (const label of genreOpts.labels) {
        if (label.checked) { selected++; continue; }
        if (selected >= 3) break; // Max 3 typically
        if (targets.some(t => label.text.includes(t))) {
          console.log(`  Selecting: "${label.text}"`);
          await clickAt(send, label.x, label.y);
          selected++;
          await sleep(300);
        }
      }
      // If we didn't select enough, pick first available
      if (selected === 0) {
        for (const label of genreOpts.labels) {
          if (!label.checked && selected < 3) {
            console.log(`  Selecting (fallback): "${label.text}"`);
            await clickAt(send, label.x, label.y);
            selected++;
            await sleep(300);
          }
        }
      }
    }
  }

  // Verify all metadata is now filled
  await sleep(500);
  r = await eval_(`
    const tabs = Array.from(document.querySelectorAll('.metadata-names-list li'))
      .map(li => ({
        text: li.textContent.trim(),
        class: li.className || '',
        isInvalid: (li.className || '').includes('invalid')
      }));
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify({ tabs, errors });
  `);
  console.log("\nMetadata validation:", r);
  const validation = JSON.parse(r);

  // Check all form values
  r = await eval_(`
    return JSON.stringify({
      title: document.querySelector('input[name="gig[title]"]')?.value || '',
      category: document.querySelector('input[name="gig[category_id]"]')?.value || '',
      subcategory: document.querySelector('input[name="gig[sub_category_id]"]')?.value || '',
      tags: document.querySelector('input[name="gig[tag_list]"]')?.value || '',
      serviceType: document.querySelector('.gig-service-type-wrapper [class*="singleValue"]')?.textContent?.trim() || ''
    });
  `);
  console.log("Form state:", r);

  // Scroll to and click Save & Continue
  const hasBlockingErrors = validation.errors.some(e =>
    e.includes('metadata') || e.includes('I will') || e.includes('service type') || e.includes('Mandatory'));

  if (!hasBlockingErrors) {
    console.log("\nNo blocking errors! Saving...");
  } else {
    console.log("\nStill have errors but attempting save anyway...");
  }

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'scrolling to button';
    }
    return 'no button';
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
    console.log(`Clicking Save & Continue at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        errors: Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100)),
        body: (document.body?.innerText || '').substring(0, 600)
      });
    `);
    console.log("\nAfter save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
