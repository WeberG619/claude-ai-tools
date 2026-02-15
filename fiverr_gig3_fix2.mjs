// Fix gig #3: subcategory, tags, metadata - attempt 2
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

  // === FIX SUBCATEGORY ===
  console.log("=== Subcategory ===");

  // Find the subcategory control specifically (the one with "Select A Subcategory" placeholder)
  let r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="category-selector__control"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2),
        w: Math.round(el.getBoundingClientRect().width)
      }));
    return JSON.stringify(controls);
  `);
  console.log("Category controls:", r);
  const controls = JSON.parse(r);

  // The subcategory one contains "Select A Subcategory" or is the second control
  const subControl = controls.find(c => c.text.includes("Subcategory")) || controls[1];
  if (subControl) {
    console.log(`Clicking subcategory at (${subControl.x}, ${subControl.y}): "${subControl.text}"`);
    await clickAt(send, subControl.x, subControl.y);
    await sleep(1500);

    // Now look for options - should be subcategories of Writing & Translation
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
      await sleep(1500);
      console.log("Selected:", resume.text);
    } else {
      console.log("Options:", subOpts.map(o => o.text));
      // If we got category options again, try clicking further right
      if (subOpts.some(o => o.text.includes('Graphics') || o.text.includes('Digital Marketing'))) {
        console.log("Got category options! Closing and trying direct approach...");
        // Press Escape to close
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
        await sleep(500);

        // Try clicking at the known subcategory position (x:802, y:602 from previous run)
        console.log("Clicking at (802, 602) for subcategory");
        await clickAt(send, 802, 602);
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
        console.log("Options after direct click:", r);
        const opts2 = JSON.parse(r);
        const resume2 = opts2.find(o => o.text.includes('Resume'));
        if (resume2) {
          await clickAt(send, resume2.x, resume2.y);
          await sleep(1500);
          console.log("Selected:", resume2.text);
        } else {
          console.log("Still no Resume option. All options:", opts2.map(o => o.text));
        }
      }
    }
  }

  // Check if subcategory was set
  await sleep(500);
  r = await eval_(`
    const controls = Array.from(document.querySelectorAll('[class*="category-selector__single-value"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());
    return JSON.stringify(controls);
  `);
  console.log("Current category values:", r);

  // === SERVICE TYPE (may appear after subcategory) ===
  console.log("\n=== Service Type ===");
  await sleep(1000);
  r = await eval_(`
    const wrapper = document.querySelector('.gig-service-type-wrapper');
    if (!wrapper) return JSON.stringify({ error: 'no wrapper' });
    const selects = wrapper.querySelectorAll('select, [class*="control"], [class*="dropdown"]');
    const items = Array.from(selects).map(el => ({
      tag: el.tagName, class: (el.className || '').substring(0, 50),
      text: el.textContent?.trim()?.substring(0, 30) || '',
      x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
      y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
    }));
    return JSON.stringify(items);
  `);
  console.log("Service type elements:", r);

  // === FIX TAGS ===
  console.log("\n=== Tags ===");

  // First check current tags
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"], .react-tags__selected-tag-name'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(tags);
  `);
  console.log("Current tags:", r);

  // Try using insertText approach (which worked for description/title)
  r = await eval_(`
    const tagInput = document.querySelector('.react-tags__search-input input');
    if (tagInput) {
      tagInput.scrollIntoView({ block: 'center' });
      tagInput.focus();
      const rect = tagInput.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no input' });
  `);
  console.log("Tag input:", r);
  const tagPos = JSON.parse(r);

  if (!tagPos.error) {
    const newTags = ["resume writing", "cv writing", "cover letter", "linkedin", "career"];
    for (const tag of newTags) {
      // Click the input to focus it
      await clickAt(send, tagPos.x, tagPos.y);
      await sleep(300);

      // Use insertText which works with React inputs
      await send("Input.insertText", { text: tag });
      await sleep(1200);

      // Check for suggestions
      r = await eval_(`
        const suggestions = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="suggestion"]'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
          .map(el => ({
            text: el.textContent.trim().substring(0, 30),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(suggestions);
      `);
      const suggestions = JSON.parse(r);
      console.log(`"${tag}" suggestions:`, r);

      if (suggestions.length > 0) {
        await clickAt(send, suggestions[0].x, suggestions[0].y);
        console.log(`  -> Selected: "${suggestions[0].text}"`);
      } else {
        // Try pressing Enter
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
        console.log(`  -> Enter (no suggestion)`);
      }
      await sleep(500);

      // Clear the input for next tag
      await eval_(`
        const tagInput = document.querySelector('.react-tags__search-input input');
        if (tagInput) { tagInput.value = ''; tagInput.dispatchEvent(new Event('input', { bubbles: true })); }
      `);
      await sleep(200);
    }
  }

  // Verify tags
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, [class*="tag-item"], .react-tags__selected-tag-name'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 20));
    return JSON.stringify(tags);
  `);
  console.log("Tags after fix:", r);

  // === METADATA ===
  console.log("\n=== Metadata ===");
  r = await eval_(`
    // Scroll down to find metadata
    window.scrollTo(0, document.documentElement.scrollHeight);
    return 'scrolled';
  `);
  await sleep(1000);

  r = await eval_(`
    const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => {
        const label = (el.closest('label') || el.parentElement)?.textContent?.trim() || '';
        const rect = el.getBoundingClientRect();
        return {
          label: label.substring(0, 30),
          checked: el.checked,
          x: Math.round(rect.x + 10),
          y: Math.round(rect.y + 10)
        };
      });
    return JSON.stringify(checkboxes);
  `);
  console.log("All checkboxes:", r);

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
