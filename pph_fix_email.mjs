// Fix PPH email to business email and finish profile
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
  let { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected to PPH\n");

  // Check current page state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("Current page:", r);

  // First check if there's an account/settings page to change email
  // Navigate to settings
  await send("Page.navigate", { url: "https://www.peopleperhour.com/site/account_setting" });
  await sleep(3000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000),
      inputs: Array.from(document.querySelectorAll('input'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden')
        .map(i => ({ type: i.type, name: i.name, id: i.id, value: i.type !== 'password' ? i.value : '***', placeholder: i.placeholder }))
    });
  `);
  console.log("\nSettings page:", r);

  const state = JSON.parse(r);

  // Check if there's an email field we can change
  const emailInput = state.inputs.find(i => i.type === 'email' || i.name?.includes('email') || i.value?.includes('@'));
  if (emailInput) {
    console.log("\nFound email field:", emailInput.name || emailInput.id, "=", emailInput.value);
    const selector = emailInput.id ? `#${emailInput.id}` :
                     emailInput.name ? `input[name="${emailInput.name}"]` : 'input[type="email"]';

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
    await send("Input.insertText", { text: "weber@bimopsstudio.com" });
    await sleep(500);
    console.log("  Email changed to weber@bimopsstudio.com");

    // Look for save button
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button, input[type="submit"]'))
        .find(b => b.offsetParent !== null && (b.textContent?.toLowerCase()?.includes('save') || b.textContent?.toLowerCase()?.includes('update')));
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent.trim() });
      }
      return null;
    `);
    if (r) {
      const pos = JSON.parse(r);
      console.log(`  Clicking "${pos.text}"...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(3000);
    }
  } else {
    console.log("\nNo email field found on settings page. May need to navigate elsewhere.");
    console.log("Page content:", state.preview.substring(0, 500));
  }

  // Now go back to profile application to fix skills
  console.log("\n\nNavigating back to profile application...");
  await send("Page.navigate", { url: "https://www.peopleperhour.com/member-application" });
  await sleep(3000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1500),
      inputs: Array.from(document.querySelectorAll('input, textarea, select'))
        .filter(i => i.offsetParent !== null && i.type !== 'hidden' && !i.name?.includes('recaptcha'))
        .map(i => ({ tag: i.tagName, type: i.type, name: i.name, id: i.id, value: i.type !== 'password' ? i.value?.substring(0, 30) : '***', placeholder: i.placeholder?.substring(0, 30) }))
    });
  `);
  console.log("Profile app:", r);

  // Try adding skills with the right approach - check what type of widget it is
  r = await eval_(`
    // Check for select2 or other skill widget
    const s2 = document.querySelector('.select2-container');
    const skillArea = document.querySelector('[class*="skill"]');
    const allDropdowns = Array.from(document.querySelectorAll('.select2-input, .select2-search-field input, .select2-choices input'));
    return JSON.stringify({
      select2: !!s2,
      skillArea: !!skillArea,
      dropdowns: allDropdowns.map(d => ({ tag: d.tagName, class: d.className?.substring(0, 50), name: d.name }))
    });
  `);
  console.log("\nSkill widget:", r);

  // Try to add skills via the select2 widget
  const skills = ["Article Writing", "Content Writing", "Data Entry", "Research", "Excel", "Copywriting", "Proofreading"];

  for (const skill of skills) {
    // Click into the select2 search area
    r = await eval_(`
      const searchField = document.querySelector('.select2-search-field input, .select2-input, input.select2-input');
      if (searchField) {
        searchField.focus();
        searchField.click();
        const rect = searchField.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      // Try clicking the select2 container
      const container = document.querySelector('.select2-container, .select2-choices');
      if (container) {
        container.click();
        const rect = container.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      return null;
    `);

    if (!r) {
      console.log("  Cannot find skill input widget");
      break;
    }

    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(300);

    // Type the skill name character by character
    for (const char of skill) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
      await send("Input.dispatchKeyEvent", { type: "char", text: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(30);
    }
    await sleep(1500);

    // Check for dropdown results
    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-result, .select2-results li, .select2-result-label'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0);
      if (results.length > 0) {
        const match = results.find(r => r.textContent.toLowerCase().includes(${JSON.stringify(skill.toLowerCase())})) || results[0];
        match.click();
        return 'selected: ' + match.textContent.trim().substring(0, 50);
      }
      return 'no results (' + document.querySelectorAll('.select2-results li').length + ' items)';
    `);
    console.log(`  ${skill}: ${r}`);
    await sleep(500);
  }

  // Final check
  r = await eval_(`
    const skillTags = Array.from(document.querySelectorAll('.select2-search-choice, [class*="tag"], [class*="chip"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 30));
    return JSON.stringify({
      skills: skillTags,
      jobTitle: document.querySelector('input[name="MemberProfile[job_title]"]')?.value || '',
      rate: document.querySelector('input[name="MemberProfile[real_hour_rate]"]')?.value || ''
    });
  `);
  console.log("\nProfile state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
