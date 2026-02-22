// Fix gig #3 tags only - category and subcategory already set
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

  // Verify current state
  let r = await eval_(`
    const vals = Array.from(document.querySelectorAll('[class*="category-selector__single-value"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim());
    return JSON.stringify(vals);
  `);
  console.log("Category values:", r);

  // Remove existing bad tags by clicking X buttons
  console.log("\n=== Remove existing tags ===");
  for (let i = 0; i < 5; i++) {
    r = await eval_(`
      const removeBtn = document.querySelector('.react-tags__selected-tag');
      if (removeBtn) {
        removeBtn.click();
        return 'removed one';
      }
      return 'none left';
    `);
    console.log(r);
    if (r === 'none left') break;
    await sleep(300);
  }

  // Add tags one by one
  console.log("\n=== Add tags ===");
  const tags = ["resume", "cover letter", "cv", "linkedin", "career"];

  for (const tag of tags) {
    // Focus the tag input
    r = await eval_(`
      const input = document.querySelector('.react-tags__search-input input');
      if (input) {
        input.scrollIntoView({ block: 'center' });
        input.focus();
        input.value = '';
        const rect = input.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no input' });
    `);
    const pos = JSON.parse(r);
    if (pos.error) { console.log("No tag input found!"); break; }

    // Click input
    await clickAt(send, pos.x, pos.y);
    await sleep(200);

    // Type using insertText
    await send("Input.insertText", { text: tag });
    await sleep(1500);

    // Check what the input value is now
    r = await eval_(`
      const input = document.querySelector('.react-tags__search-input input');
      return input ? input.value : 'no input';
    `);
    console.log(`Input value after typing "${tag}":`, r);

    // Check for suggestions
    r = await eval_(`
      const sug = Array.from(document.querySelectorAll('.react-tags__suggestions li, [class*="react-tags__suggestions"] li'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
        .map(el => ({
          text: el.textContent.trim().substring(0, 30),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify(sug);
    `);
    const suggestions = JSON.parse(r);
    console.log(`  Suggestions:`, suggestions.map(s => s.text));

    if (suggestions.length > 0) {
      const exact = suggestions.find(s => s.text.toLowerCase().includes(tag.toLowerCase()));
      const pick = exact || suggestions[0];
      await clickAt(send, pick.x, pick.y);
      console.log(`  -> Selected: "${pick.text}"`);
    } else {
      // No suggestion - try Tab then Enter
      console.log(`  -> No suggestions, trying Tab/Enter`);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Tab", code: "Tab" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Tab", code: "Tab" });
      await sleep(200);
    }
    await sleep(500);
  }

  // Verify tags
  await sleep(500);
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.react-tags__selected-tag, .react-tags__selected-tag-name'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify(tags);
  `);
  console.log("\nFinal tags:", r);

  // Check the entire tag section DOM structure
  r = await eval_(`
    const tagSection = document.querySelector('.react-tags');
    if (tagSection) return tagSection.outerHTML.substring(0, 500);
    return 'no .react-tags found';
  `);
  console.log("\nTag section HTML:", r);

  // Try to save
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  await sleep(800);
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
