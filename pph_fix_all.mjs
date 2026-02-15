// Fix PeoplePerHour application - proper Select2 handling + field fixes
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
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com/member-application");
  console.log("Connected\n");

  // Step 1: Fix Job Title (clear properly first using execCommand)
  console.log("=== 1. Fixing Job Title ===");
  let r = await eval_(`
    const el = document.getElementById('MemberProfile_job_title');
    if (el) {
      el.focus();
      el.select();
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, 'Writer & Data Specialist');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'Set to: ' + el.value;
    }
    return 'not found';
  `);
  console.log(r);
  await sleep(300);

  // Step 2: Fix Hourly Rate
  console.log("\n=== 2. Fixing Hourly Rate ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_real_hour_rate');
    if (el) {
      el.focus();
      el.select();
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, '28');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'Set to: ' + el.value;
    }
    return 'not found';
  `);
  console.log(r);
  await sleep(300);

  // Step 3: Investigate Select2 structure deeply
  console.log("\n=== 3. Investigating Select2 for Skills ===");
  r = await eval_(`
    // Find all select2 containers and identify which is skills vs languages
    const containers = Array.from(document.querySelectorAll('.select2-container'));
    const info = containers.map((c, i) => {
      const prevLabel = c.previousElementSibling?.textContent?.trim() || '';
      const parentText = c.parentElement?.querySelector('label, h3, h4, .title')?.textContent?.trim() || '';
      const input = c.querySelector('input.select2-input, input[type="text"]');
      const hiddenSelect = c.previousElementSibling?.tagName === 'SELECT' ? c.previousElementSibling : null;
      const selectId = hiddenSelect?.id || hiddenSelect?.name || '';
      return {
        index: i,
        prevLabel: prevLabel.substring(0, 50),
        parentText: parentText.substring(0, 50),
        inputPlaceholder: input?.placeholder || input?.getAttribute('placeholder') || '',
        hasInput: !!input,
        selectId,
        selectName: hiddenSelect?.name || '',
        classes: c.className.substring(0, 80),
        choices: c.querySelectorAll('.select2-search-choice').length
      };
    });

    // Also check for hidden select elements
    const hiddenSelects = Array.from(document.querySelectorAll('select'))
      .map(s => ({ id: s.id, name: s.name, multiple: s.multiple, optCount: s.options?.length || 0 }));

    return JSON.stringify({ containers: info, hiddenSelects, jqVersion: typeof jQuery !== 'undefined' ? jQuery.fn.jquery : 'none' });
  `);
  console.log(r);

  const structure = JSON.parse(r);
  console.log("\nSelect2 containers:");
  structure.containers.forEach(c => {
    console.log(`  [${c.index}] placeholder="${c.inputPlaceholder}" selectId="${c.selectId}" choices=${c.choices}`);
  });
  console.log("\nHidden selects:");
  structure.hiddenSelects.forEach(s => {
    console.log(`  id="${s.id}" name="${s.name}" multiple=${s.multiple} options=${s.optCount}`);
  });

  // Step 4: Try to add skills using jQuery Select2 API
  console.log("\n=== 4. Adding Skills via Select2 API ===");

  // First, find which select element is for skills
  r = await eval_(`
    if (typeof jQuery === 'undefined') return 'no jQuery';

    // Try to find skill-related select elements
    const selects = jQuery('select').toArray();
    const skillSelect = selects.find(s => {
      const id = s.id || s.name || '';
      const label = jQuery(s).closest('.form-group, .control-group').find('label').text();
      return id.toLowerCase().includes('skill') || label.toLowerCase().includes('skill');
    });

    if (skillSelect) {
      return JSON.stringify({
        id: skillSelect.id,
        name: skillSelect.name,
        isSelect2: jQuery(skillSelect).hasClass('select2-offscreen') || jQuery(skillSelect).data('select2') !== undefined,
        currentVals: jQuery(skillSelect).val()
      });
    }

    // Also look at what's connected to the s2id_autogen1 input
    const autogen = document.getElementById('s2id_autogen1');
    if (autogen) {
      const container = autogen.closest('.select2-container');
      const relatedSelect = container?.previousElementSibling;
      if (relatedSelect?.tagName === 'SELECT') {
        return JSON.stringify({
          id: relatedSelect.id,
          name: relatedSelect.name,
          tagName: relatedSelect.tagName,
          isHidden: relatedSelect.style.display === 'none' || relatedSelect.offsetParent === null
        });
      }
    }

    return 'no skill select found';
  `);
  console.log("Skill select:", r);

  // Try using the select2 search with keyboard events
  console.log("\n=== 5. Adding Skills via Keyboard Events ===");
  const skills = [
    "Article Writing", "Content Writing", "Data Entry",
    "Research", "Microsoft Excel", "Copywriting",
    "Technical Writing", "Proofreading", "Blog Writing"
  ];

  for (const skill of skills) {
    console.log(`\n  Trying: "${skill}"`);

    // Focus the skills input
    r = await eval_(`
      const input = document.getElementById('s2id_autogen1');
      if (!input) return 'input not found';
      input.scrollIntoView({ block: 'center' });
      input.value = '';
      input.focus();
      return 'focused, value cleared';
    `);
    console.log(`    ${r}`);
    await sleep(300);

    // Type character by character to trigger search
    for (const char of skill) {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
      await send("Input.dispatchKeyEvent", { type: "char", text: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(50);
    }
    await sleep(2000); // Wait for AJAX search

    // Check what results appeared
    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-results li, .select2-results .select2-result-label'))
        .filter(el => {
          if (!el.offsetParent && el.parentElement?.offsetParent === null) return false;
          const text = el.textContent.trim();
          return text.length > 0 && !text.includes('Searching') && text !== 'Type something to start searching';
        });

      const resultTexts = results.map(r => r.textContent.trim().substring(0, 60));

      // Also check the dropdown container visibility
      const dropdown = document.querySelector('.select2-drop-active, .select2-with-searchbox');
      const isOpen = dropdown && dropdown.style.display !== 'none';

      return JSON.stringify({
        count: results.length,
        texts: resultTexts.slice(0, 5),
        dropdownOpen: isOpen,
        inputValue: document.getElementById('s2id_autogen1')?.value || ''
      });
    `);
    console.log(`    Results: ${r}`);

    const resultInfo = JSON.parse(r);
    if (resultInfo.count > 0 && !resultInfo.texts[0]?.includes('No matches')) {
      // Click the first valid result
      r = await eval_(`
        const results = Array.from(document.querySelectorAll('.select2-results li'))
          .filter(el => {
            const text = el.textContent.trim();
            return text.length > 0 && !text.includes('Searching') && text !== 'Type something to start searching' && !text.includes('No matches');
          });
        if (results.length > 0) {
          results[0].click();
          return 'clicked: ' + results[0].textContent.trim().substring(0, 50);
        }
        return 'nothing to click';
      `);
      console.log(`    ${r}`);
    } else {
      // Press Escape to close dropdown
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape" });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape" });
      console.log(`    No valid results, skipped`);
    }
    await sleep(500);
  }

  // Check final skill chips
  console.log("\n=== Skills Added ===");
  r = await eval_(`
    const chips = Array.from(document.querySelectorAll('.select2-search-choice'))
      .map(c => c.textContent.replace(/×/g, '').trim())
      .filter(t => t.length > 0);
    return JSON.stringify(chips);
  `);
  console.log(r);

  // Step 6: Add Language - English
  console.log("\n=== 6. Adding Language ===");
  r = await eval_(`
    const input = document.getElementById('s2id_autogen2');
    if (input) {
      input.scrollIntoView({ block: 'center' });
      input.value = '';
      input.focus();
      return 'focused language input';
    }
    return 'language input not found';
  `);
  console.log(r);
  await sleep(300);

  if (r.includes('focused')) {
    for (const char of "English") {
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
      await send("Input.dispatchKeyEvent", { type: "char", text: char });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
      await sleep(50);
    }
    await sleep(2000);

    r = await eval_(`
      const results = Array.from(document.querySelectorAll('.select2-results li'))
        .filter(el => el.textContent.trim().length > 0 && !el.textContent.includes('Searching') && !el.textContent.includes('No matches'));
      const texts = results.map(r => r.textContent.trim().substring(0, 50));
      if (results.length > 0) {
        const english = results.find(r => r.textContent.includes('English')) || results[0];
        english.click();
        return 'selected: ' + english.textContent.trim().substring(0, 50);
      }
      return 'no results: ' + texts.join(', ');
    `);
    console.log(r);
  }

  // Final state
  console.log("\n=== Final State ===");
  r = await eval_(`
    return JSON.stringify({
      jobTitle: document.getElementById('MemberProfile_job_title')?.value,
      about: (document.getElementById('MemberProfile_about')?.value || '').substring(0, 80) + '...',
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value,
      location: document.querySelector('input[name="location_combo"]')?.value,
      skills: Array.from(document.querySelectorAll('.select2-container'))
        .map((c, i) => ({
          index: i,
          choices: Array.from(c.querySelectorAll('.select2-search-choice')).map(ch => ch.textContent.replace(/×/g, '').trim())
        }))
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
