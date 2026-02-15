// Check current PPH state and fix corrupted fields
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
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected\n");

  // Check current state
  console.log("=== Current State ===");
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      title: document.title,
      jobTitle: document.getElementById('MemberProfile_job_title')?.value || '',
      about: (document.getElementById('MemberProfile_about')?.value || '').substring(0, 100),
      location: document.querySelector('input[name="location_combo"]')?.value || '',
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value || '',
      skills: Array.from(document.querySelectorAll('.select2-search-choice')).map(c => c.textContent.replace(/×/g, '').trim()).filter(t => t.length > 0),
      languages: (() => {
        const containers = document.querySelectorAll('.select2-container');
        if (containers.length >= 2) {
          return Array.from(containers[1].querySelectorAll('.select2-search-choice')).map(c => c.textContent.replace(/×/g, '').trim()).filter(t => t.length > 0);
        }
        return [];
      })(),
      emailVerified: !document.body.innerText.includes('check your inbox'),
      submitDisabled: document.querySelector('button[type="submit"], input[type="submit"]')?.disabled || false,
      hasPhoto: !!document.querySelector('[class*="profile-photo"] img, [class*="ProfilePhoto"] img')
    });
  `);
  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Job Title:", JSON.stringify(state.jobTitle));
  console.log("About:", state.about + "...");
  console.log("Location:", state.location);
  console.log("Rate:", state.rate);
  console.log("Skills:", state.skills);
  console.log("Languages:", state.languages);
  console.log("Email verified:", state.emailVerified);
  console.log("Submit disabled:", state.submitDisabled);

  // Step 1: Fix Job Title using native setter
  console.log("\n=== Fixing Job Title ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_job_title');
    if (!el) return 'not found';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, 'Writer & Data Specialist');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'Set to: ' + el.value;
  `);
  console.log(r);

  // Step 2: Fix Hourly Rate
  console.log("\n=== Fixing Hourly Rate ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_real_hour_rate');
    if (!el) return 'not found';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, '28');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'Set to: ' + el.value;
  `);
  console.log(r);

  // Step 3: Try skills with jQuery Select2 API
  console.log("\n=== Adding Skills via jQuery ===");

  // First, understand the Select2 structure better
  r = await eval_(`
    const $ = jQuery;

    // Find the actual select element behind the skills Select2
    const container = document.querySelectorAll('.select2-container')[0];
    const prevSibling = container?.previousElementSibling;

    // Check for data-ajax-url or other config on the Select2
    const s2input = container?.querySelector('input.select2-input');

    // Try to find the Select2 element's data
    let s2Data = null;
    try {
      // The select2 stores its config in $.data
      const allS2 = $('[class*="select2"]').filter('input, select, [data-select2]');
      s2Data = allS2.map(function() { return { id: this.id, tag: this.tagName, name: this.name }; }).get();
    } catch(e) {}

    // Check for ajax URL in the Select2 config
    let ajaxUrl = '';
    try {
      const s2Obj = $(s2input).data('select2') || $(container).data('select2');
      if (s2Obj?.opts?.ajax?.url) ajaxUrl = s2Obj.opts.ajax.url;
    } catch(e) {}

    // Try to get select2 data from the container
    let containerData = null;
    try {
      containerData = $(container).data();
    } catch(e) {}

    return JSON.stringify({
      prevSiblingTag: prevSibling?.tagName,
      prevSiblingId: prevSibling?.id,
      prevSiblingClass: prevSibling?.className?.substring(0, 100),
      s2InputClass: s2input?.className?.substring(0, 100),
      s2Data,
      ajaxUrl,
      containerDataKeys: containerData ? Object.keys(containerData) : []
    });
  `);
  console.log("Select2 structure:", r);

  // Try to find the hidden input that Select2 is attached to
  r = await eval_(`
    const $ = jQuery;

    // Look for hidden inputs near the skills section
    const hiddenInputs = $('input[type="hidden"]').filter(function() {
      const name = $(this).attr('name') || '';
      return name.includes('skill') || name.includes('Skill') || name.includes('tag');
    });

    const result = hiddenInputs.map(function() {
      return {
        name: $(this).attr('name'),
        id: $(this).attr('id'),
        val: $(this).val()?.substring(0, 100),
        hasSelect2: !!$(this).data('select2')
      };
    }).get();

    // Also check all elements with select2 data
    const s2Elements = $('*').filter(function() { return !!$(this).data('select2'); });
    const s2Info = s2Elements.map(function() {
      const d = $(this).data('select2');
      return {
        tag: this.tagName,
        id: this.id,
        name: this.name || $(this).attr('name'),
        opts: d?.opts ? {
          ajax: !!d.opts.ajax,
          ajaxUrl: d.opts.ajax?.url?.substring(0, 80),
          multiple: d.opts.multiple,
          tags: d.opts.tags,
          placeholder: d.opts.placeholder?.substring(0, 50),
          minimumInputLength: d.opts.minimumInputLength
        } : null
      };
    }).get();

    return JSON.stringify({ hiddenInputs: result, select2Elements: s2Info });
  `);
  console.log("Select2 elements:", r);

  const s2Info = JSON.parse(r);
  console.log("\nSelect2 configs:");
  s2Info.select2Elements.forEach(el => {
    console.log(`  ${el.tag}#${el.id} name="${el.name}"`);
    if (el.opts) {
      console.log(`    ajax: ${el.opts.ajax} url: ${el.opts.ajaxUrl}`);
      console.log(`    multiple: ${el.opts.multiple} tags: ${el.opts.tags}`);
      console.log(`    placeholder: "${el.opts.placeholder}" minInput: ${el.opts.minimumInputLength}`);
    }
  });

  // If we found the Select2 element, try to trigger a search programmatically
  if (s2Info.select2Elements.length > 0) {
    const skillEl = s2Info.select2Elements[0];
    console.log(`\nTrying to add skills to ${skillEl.tag}#${skillEl.id}...`);

    if (skillEl.opts?.ajax) {
      // AJAX-based Select2 - need to call the AJAX endpoint directly
      console.log("Skills use AJAX search, URL:", skillEl.opts.ajaxUrl);

      // Try fetching skills data directly
      r = await eval_(`
        const $ = jQuery;
        return new Promise((resolve) => {
          $.ajax({
            url: ${JSON.stringify(skillEl.opts.ajaxUrl || '/site/ajaxSearchTag')},
            data: { term: 'data entry', type: 'skill' },
            dataType: 'json',
            success: function(data) { resolve(JSON.stringify(data)); },
            error: function(xhr, status, err) { resolve('error: ' + status + ' ' + err + ' ' + xhr.responseText?.substring(0, 200)); }
          });
        });
      `);
      console.log("AJAX skill search result:", r?.substring(0, 500));
    }

    // Try to use select2's programmatic API to add a value
    r = await eval_(`
      const $ = jQuery;
      const selector = ${JSON.stringify('#' + skillEl.id || 'input[name="' + skillEl.name + '"]')};
      const el = $(selector);

      if (el.length === 0) return 'element not found: ' + selector;

      // Try select2 trigger
      try {
        // For tags/tokenizer mode:
        const s2 = el.data('select2');
        if (s2) {
          // Try opening the dropdown and triggering search
          s2.open();
          return 'opened select2';
        }
      } catch(e) {
        return 'error: ' + e.message;
      }
      return 'no select2 data';
    `);
    console.log("Open result:", r);

    if (r === 'opened select2') {
      await sleep(500);

      // Now type in the search
      r = await eval_(`
        const searchInput = document.querySelector('.select2-drop-active .select2-input, .select2-search input');
        if (searchInput) {
          return JSON.stringify({
            found: true,
            class: searchInput.className.substring(0, 80),
            rect: { x: searchInput.getBoundingClientRect().x, y: searchInput.getBoundingClientRect().y, w: searchInput.getBoundingClientRect().width }
          });
        }
        return JSON.stringify({ found: false });
      `);
      console.log("Search input after open:", r);

      const searchInfo = JSON.parse(r);
      if (searchInfo.found) {
        // Type into the search input
        const skills = ['Data Entry', 'Excel', 'Content Writing', 'Copywriting', 'Article Writing',
                        'Research', 'Technical Writing', 'Proofreading', 'Blog Writing'];

        for (const skill of skills) {
          console.log(`\n  Adding: "${skill}"`);

          // Open select2
          await eval_(`
            const $ = jQuery;
            const el = $(${JSON.stringify('#' + skillEl.id || 'input[name="' + skillEl.name + '"]')});
            const s2 = el.data('select2');
            if (s2) s2.open();
          `);
          await sleep(300);

          // Focus the active search input and type
          await eval_(`
            const searchInput = document.querySelector('.select2-drop-active .select2-input, .select2-search input, .select2-focused input');
            if (searchInput) { searchInput.value = ''; searchInput.focus(); }
          `);
          await sleep(200);

          // Type with key events
          for (const char of skill) {
            await send("Input.dispatchKeyEvent", { type: "keyDown", key: char, text: char });
            await send("Input.dispatchKeyEvent", { type: "char", text: char });
            await send("Input.dispatchKeyEvent", { type: "keyUp", key: char });
            await sleep(30);
          }
          await sleep(1500);

          // Check results
          r = await eval_(`
            const results = Array.from(document.querySelectorAll('.select2-results li, .select2-result'))
              .filter(el => {
                const display = window.getComputedStyle(el).display;
                return display !== 'none' && el.textContent.trim().length > 0;
              });
            const texts = results.map(r => r.textContent.trim().substring(0, 50));
            if (results.length > 0) {
              const match = results.find(r => !r.textContent.includes('Searching') && !r.textContent.includes('No matches') && r.textContent.trim().length > 0);
              if (match) {
                match.click();
                return 'selected: ' + match.textContent.trim();
              }
            }
            return 'no results: ' + texts.join(', ');
          `);
          console.log(`    ${r}`);
          await sleep(300);
        }
      }
    }
  }

  // Final check
  console.log("\n=== Final State ===");
  r = await eval_(`
    return JSON.stringify({
      jobTitle: document.getElementById('MemberProfile_job_title')?.value,
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value,
      about: (document.getElementById('MemberProfile_about')?.value || '').substring(0, 80),
      location: document.querySelector('input[name="location_combo"]')?.value,
      skills: Array.from(document.querySelectorAll('.select2-search-choice')).map(c => c.textContent.replace(/×/g, '').trim()).filter(t => t.length > 0),
      allHiddenSkills: Array.from(document.querySelectorAll('input[type="hidden"]'))
        .filter(i => (i.name || '').includes('skill') || (i.name || '').includes('tag'))
        .map(i => i.name + '=' + (i.value || '').substring(0, 50))
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
