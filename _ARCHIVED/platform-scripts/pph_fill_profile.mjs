// Fill PeoplePerHour freelancer application profile
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com/member-application");
  console.log("Connected to PPH application\n");

  // Fill Job Title
  console.log("Filling job title...");
  let r = await eval_(`
    const input = document.querySelector('input[name="MemberProfile[job_title]"]');
    if (input) { input.focus(); input.click(); }
    return input ? 'focused' : 'not found';
  `);
  await sleep(200);
  await send("Input.insertText", { text: "Writer & Data Specialist" });
  await sleep(300);
  console.log("  Done");

  // Fill About You (textarea)
  console.log("\nFilling about...");
  r = await eval_(`
    const ta = document.querySelector('textarea[name*="text"], textarea');
    if (ta) {
      ta.focus();
      ta.click();
      return 'focused textarea';
    }
    // Try contenteditable
    const editable = document.querySelector('[contenteditable="true"]');
    if (editable) {
      editable.focus();
      return 'focused contenteditable';
    }
    return 'not found';
  `);
  console.log("  ", r);
  await sleep(200);

  const aboutText = `Professional writer and data specialist with AI-enhanced workflows. I deliver high-quality content, data processing, and research with fast turnaround times.

Services: article writing, blog posts, technical writing, data entry, Excel spreadsheets, research reports, copywriting, editing, and proofreading.

I combine traditional expertise with modern AI tools for faster delivery while maintaining exceptional quality.`;

  await send("Input.insertText", { text: aboutText });
  await sleep(500);
  console.log("  About text entered");

  // Fill hourly rate (change from £6 to something reasonable - $35 USD ≈ £28)
  console.log("\nSetting hourly rate...");
  r = await eval_(`
    const input = document.querySelector('input[name="MemberProfile[real_hour_rate]"]');
    if (input) {
      input.focus();
      input.click();
      return 'focused rate input, current: ' + input.value;
    }
    return 'not found';
  `);
  console.log("  ", r);
  await sleep(200);
  // Select all and replace
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(100);
  await send("Input.insertText", { text: "28" });
  await sleep(300);

  // Add skills using the skill search
  console.log("\nAdding skills...");
  const skills = [
    "Article Writing",
    "Content Writing",
    "Data Entry",
    "Research",
    "Excel",
    "Copywriting",
    "Technical Writing",
    "Proofreading",
    "Blog Writing",
    "Report Writing"
  ];

  for (const skill of skills) {
    // Focus the skill search input
    r = await eval_(`
      const input = document.querySelector('input[name="s2id_autogen1"], input[placeholder*="skill"], .select2-input');
      if (input) { input.focus(); input.click(); return 'focused'; }
      return 'not found';
    `);

    if (r === 'not found') {
      console.log("  Skill input not found, trying alternative...");
      r = await eval_(`
        const inputs = Array.from(document.querySelectorAll('input'))
          .filter(i => i.placeholder?.toLowerCase().includes('skill') || i.className?.includes('select2'));
        return JSON.stringify(inputs.map(i => ({ name: i.name, placeholder: i.placeholder, class: i.className?.substring(0, 50) })));
      `);
      console.log("  Available:", r);
      break;
    }

    await sleep(200);
    // Clear and type skill name
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(50);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
    await sleep(100);
    await send("Input.insertText", { text: skill });
    await sleep(1500); // Wait for dropdown

    // Click first suggestion
    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-result, .select2-results li, [class*="result"], [class*="option"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 60);
      if (results.length > 0) {
        results[0].click();
        return 'selected: ' + results[0].textContent.trim();
      }
      // Try pressing Enter
      return 'no results, will try enter';
    `);
    console.log(`  ${skill}: ${r}`);

    if (r.includes('no results')) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter" });
    }
    await sleep(500);
  }

  // Add language (English)
  console.log("\nAdding language...");
  r = await eval_(`
    const input = document.querySelector('input[name="s2id_autogen2"], input[placeholder*="Language"]');
    if (input) { input.focus(); input.click(); return 'focused'; }
    return 'not found';
  `);
  if (r === 'focused') {
    await sleep(200);
    await send("Input.insertText", { text: "English" });
    await sleep(1500);
    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-result, .select2-results li, [class*="result"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('English'));
      if (results.length > 0) { results[0].click(); return 'selected English'; }
      return 'not found';
    `);
    console.log("  ", r);
  }

  // Click Submit Application
  console.log("\nSubmitting application...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, input[type="submit"], a'))
      .find(b => b.textContent?.toLowerCase()?.includes('submit') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    return null;
  `);
  console.log("  Submit button:", r);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("  Clicked submit");
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 1000),
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100))
          .filter(t => t.length > 3)
      });
    `);
    console.log("\nResult:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
