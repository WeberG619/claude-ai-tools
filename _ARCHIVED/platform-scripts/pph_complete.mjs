// Complete PeoplePerHour profile in one pass and submit
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

async function fillField(send, eval_, selector, value) {
  await eval_(`
    const el = document.querySelector(${JSON.stringify(selector)});
    if (el) { el.focus(); el.click(); }
  `);
  await sleep(200);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
  await sleep(50);
  await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Delete", code: "Delete" });
  await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Delete", code: "Delete" });
  await sleep(100);
  await send("Input.insertText", { text: value });
  await sleep(300);
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com/member-application");
  console.log("Connected to PPH application\n");

  // 1. Job Title
  console.log("1. Job Title...");
  await fillField(send, eval_, '#MemberProfile_job_title', 'Writer & Data Specialist');
  console.log("   Done");

  // 2. Skills - try using jQuery/select2 API directly
  console.log("\n2. Skills...");
  let r = await eval_(`
    // Check if jQuery and select2 are available
    const hasJQ = typeof jQuery !== 'undefined' || typeof $ !== 'undefined';
    const jq = typeof jQuery !== 'undefined' ? jQuery : (typeof $ !== 'undefined' ? $ : null);
    if (!jq) return 'no jquery';

    // Find the select2 element for skills
    const skillSelect = jq('#skills_id, #MemberProfile_skills, select[name*="skill"]');
    if (skillSelect.length === 0) {
      // Try to find any select2 with skill-related context
      const allSelect2 = jq('.select2-container');
      return 'no skill select found. select2 containers: ' + allSelect2.length;
    }
    return 'found skill select: ' + skillSelect.attr('id');
  `);
  console.log("   jQuery check:", r);

  // Try a different approach: use the select2 search input with insertText
  const skills = ["Article Writing", "Content Writing", "Data Entry", "Research", "Excel", "Copywriting", "Technical Writing", "Proofreading", "Blog Writing", "Report Writing", "Data Analysis", "Transcription"];

  for (const skill of skills) {
    // Click the select2 container to open it
    r = await eval_(`
      const containers = Array.from(document.querySelectorAll('.select2-container'));
      // Find the one for skills (first one usually)
      const skillContainer = containers[0];
      if (skillContainer) {
        const searchField = skillContainer.querySelector('.select2-search-field, .select2-search');
        const input = skillContainer.querySelector('input.select2-input');
        if (input) {
          // Clear the input first
          input.value = '';
          input.focus();
          const rect = input.getBoundingClientRect();
          return JSON.stringify({ found: true, x: rect.x + 5, y: rect.y + rect.height/2 });
        }
        if (searchField) {
          searchField.click();
          return JSON.stringify({ found: true, clicked: 'searchField' });
        }
      }
      return JSON.stringify({ found: false, containers: containers.length });
    `);

    const info = JSON.parse(r);
    if (!info.found) {
      console.log("   Skill container not found");
      break;
    }

    if (info.x) {
      // Click the input area
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: info.x, y: info.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: info.x, y: info.y, button: "left", clickCount: 1 });
      await sleep(300);
    }

    // Clear any existing text in the search input
    await eval_(`
      const input = document.querySelector('.select2-container input.select2-input');
      if (input) { input.value = ''; input.focus(); }
    `);
    await sleep(100);

    // Use insertText to type the skill name
    await send("Input.insertText", { text: skill });
    await sleep(2000); // Give time for AJAX search

    // Check for results and click the best match
    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-results li, .select2-result'))
        .filter(el => {
          const display = window.getComputedStyle(el).display;
          return display !== 'none' && el.textContent.trim().length > 0;
        });

      const resultTexts = results.map(r => r.textContent.trim().substring(0, 50));

      if (results.length > 0) {
        // Find best match
        const match = results.find(r => r.textContent.toLowerCase().includes(${JSON.stringify(skill.toLowerCase())}));
        if (match && !match.textContent.includes('No matches')) {
          match.click();
          return 'selected: ' + match.textContent.trim().substring(0, 50);
        }
        // Click first non-"no matches" result
        const valid = results.filter(r => !r.textContent.includes('No matches'));
        if (valid.length > 0) {
          valid[0].click();
          return 'selected first: ' + valid[0].textContent.trim().substring(0, 50);
        }
        return 'only no-match results: ' + resultTexts.join(', ');
      }
      return 'no results visible';
    `);
    console.log(`   ${skill}: ${r}`);

    // If no results, press Escape and move on
    if (r.includes('no-match') || r.includes('no results')) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
      await sleep(200);
    }

    await sleep(300);
  }

  // Check what skills were added
  r = await eval_(`
    const tags = Array.from(document.querySelectorAll('.select2-search-choice'))
      .map(t => t.textContent.trim());
    return JSON.stringify(tags);
  `);
  console.log("   Added skills:", r);

  // 3. About You
  console.log("\n3. About text...");
  await fillField(send, eval_, '#MemberProfile_about',
    'Professional writer and data specialist with AI-enhanced workflows. I deliver high-quality content, data processing, and research with fast turnaround. Services include article writing, blog posts, technical writing, data entry, Excel, research reports, copywriting, editing, and proofreading. I combine expertise with modern AI tools for faster delivery and exceptional quality.');
  console.log("   Done");

  // 4. Hourly Rate
  console.log("\n4. Hourly rate...");
  await fillField(send, eval_, '#MemberProfile_real_hour_rate', '28');
  console.log("   Set to £28/hr");

  // 5. Language - try adding English
  console.log("\n5. Language...");
  r = await eval_(`
    const containers = Array.from(document.querySelectorAll('.select2-container'));
    // Language is the second select2 container
    if (containers.length >= 2) {
      const langContainer = containers[1];
      const input = langContainer.querySelector('input.select2-input');
      if (input) {
        input.value = '';
        input.focus();
        const rect = input.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + 5, y: rect.y + rect.height/2 });
      }
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(300);
    await send("Input.insertText", { text: "English" });
    await sleep(1500);

    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-results li'))
        .filter(el => window.getComputedStyle(el).display !== 'none' && el.textContent.includes('English'));
      if (results.length > 0) { results[0].click(); return 'selected English'; }
      return 'English not found';
    `);
    console.log("   ", r);
  }

  // 6. Verify all fields before submit
  console.log("\n6. Verifying form...");
  r = await eval_(`
    return JSON.stringify({
      jobTitle: document.querySelector('#MemberProfile_job_title')?.value || '',
      about: (document.querySelector('#MemberProfile_about')?.value || '').substring(0, 50) + '...',
      rate: document.querySelector('#MemberProfile_real_hour_rate')?.value || '',
      location: document.querySelector('input[name="location_combo"]')?.value || '',
      skills: Array.from(document.querySelectorAll('.select2-search-choice')).map(t => t.textContent.trim()),
      languages: Array.from(document.querySelectorAll('.select2-container')).length > 1 ?
        Array.from(document.querySelectorAll('.select2-container')[1].querySelectorAll('.select2-search-choice')).map(t => t.textContent.trim()) : []
    });
  `);
  console.log("   ", r);

  // 7. Submit
  console.log("\n7. Submitting application...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, input[type="submit"], a'))
      .find(b => b.textContent?.toLowerCase()?.includes('submit') && b.offsetParent !== null);
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    console.log(`   Clicking "${pos.text}"...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        preview: document.body.innerText.substring(0, 1000),
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="Error"], .errorSummary, .help-inline'))
          .filter(el => el.offsetParent !== null)
          .map(el => el.textContent.trim().substring(0, 100))
          .filter(t => t.length > 3)
      });
    `);
    console.log("\n   Result:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
