// Select skills on Freelancer.com new freelancer profile
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToTab(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.url.includes(urlMatch));
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

async function main() {
  let { ws, send, eval_ } = await connectToTab("freelancer.com/new-freelancer");
  console.log("Connected to Freelancer skills page\n");

  // Use the search box to add skills directly - faster than clicking categories
  const skills = [
    "Article Writing",
    "Content Writing",
    "Blog Writing",
    "Research Writing",
    "Technical Writing",
    "Data Entry",
    "Excel",
    "Data Processing",
    "Copywriting",
    "Proofreading",
    "Editing",
    "Resume Writing",
    "Report Writing",
    "BIM",
    "AutoCAD"
  ];

  for (const skill of skills) {
    console.log(`Adding skill: ${skill}...`);

    // Type into search box
    let r = await eval_(`
      const input = document.querySelector('input[placeholder*="Search a skill"], input[placeholder*="search"]');
      if (!input) return 'search input not found';
      input.focus();
      input.value = '';
      input.dispatchEvent(new Event('input', { bubbles: true }));

      const text = ${JSON.stringify(skill)};
      input.value = text;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      return 'typed: ' + text;
    `);

    if (r === 'search input not found') {
      console.log("  Search input not found!");
      break;
    }

    await sleep(1500); // Wait for suggestions

    // Click the first matching suggestion
    r = await eval_(`
      const suggestions = Array.from(document.querySelectorAll('[class*="suggestion"], [class*="dropdown"] li, [class*="autocomplete"] li, [class*="option"], [class*="result"], [role="option"], [role="listbox"] *'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60);
      if (suggestions.length > 0) {
        // Find best match
        const skill = ${JSON.stringify(skill)}.toLowerCase();
        const match = suggestions.find(s => s.textContent.trim().toLowerCase().includes(skill)) || suggestions[0];
        match.click();
        return 'selected: ' + match.textContent.trim();
      }
      // Try clicking any visible dropdown items
      const items = Array.from(document.querySelectorAll('li, [class*="item"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().toLowerCase().includes(${JSON.stringify(skill)}.toLowerCase()));
      if (items.length > 0) {
        items[0].click();
        return 'clicked item: ' + items[0].textContent.trim();
      }
      return 'no suggestions found';
    `);
    console.log("  ", r);
    await sleep(500);

    // Clear search for next skill
    await eval_(`
      const input = document.querySelector('input[placeholder*="Search a skill"], input[placeholder*="search"]');
      if (input) { input.value = ''; input.dispatchEvent(new Event('input', { bubbles: true })); }
      return 'cleared';
    `);
    await sleep(300);
  }

  // Check how many skills are selected
  console.log("\nChecking selected skills...");
  let r = await eval_(`
    const selected = Array.from(document.querySelectorAll('[class*="selected"], [class*="chip"], [class*="tag"], [class*="badge"], [class*="skill-item"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim())
      .filter(t => t.length > 2 && t.length < 50);
    const count = document.body.innerText.match(/\\d+ skills? selected/);
    return JSON.stringify({ selected: [...new Set(selected)].slice(0, 20), countText: count?.[0] || 'not found' });
  `);
  console.log("  ", r);

  // Look for Next/Continue/Done button
  console.log("\nLooking for next step...");
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button, a'))
      .filter(b => b.offsetParent !== null)
      .map(b => ({ tag: b.tagName, text: b.textContent.trim().substring(0, 40), href: b.href || '' }))
      .filter(b => b.text.length > 0 && !b.text.includes('Search'));
    return JSON.stringify(btns);
  `);
  console.log("  Buttons:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
