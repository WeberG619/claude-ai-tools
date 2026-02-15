// Add skills and language to PPH using jQuery Select2 API + direct AJAX
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

  // Step 1: Search for skills via AJAX and collect IDs
  console.log("=== 1. Fetching skill IDs via AJAX ===");
  const skillQueries = [
    'Data entry', 'Excel', 'Content Writing', 'Copywriting',
    'Article Writing', 'Research', 'Technical Writing', 'Proofreading',
    'Transcription', 'Blog Writing', 'Report Writing', 'Editing'
  ];

  let r = await eval_(`
    return new Promise(async (resolve) => {
      const $ = jQuery;
      const skillIds = [];
      const queries = ${JSON.stringify(skillQueries)};

      for (const q of queries) {
        try {
          const data = await new Promise((res, rej) => {
            $.ajax({
              url: '/memberApplication/skills',
              data: { term: q },
              dataType: 'json',
              success: res,
              error: (xhr, status, err) => rej(err)
            });
          });
          // Find best match
          if (data && data.length > 0) {
            const exact = data.find(d => d.text.toLowerCase() === q.toLowerCase()) || data[0];
            skillIds.push({ id: exact.id, text: exact.text, query: q });
          }
        } catch(e) {
          // skip
        }
      }
      resolve(JSON.stringify(skillIds));
    });
  `);

  const skills = JSON.parse(r);
  console.log(`Found ${skills.length} skills:`);
  skills.forEach(s => console.log(`  ${s.id}: "${s.text}" (from query "${s.query}")`));

  // Step 2: Set skills using Select2 data API
  console.log("\n=== 2. Setting skills via Select2 API ===");
  r = await eval_(`
    const $ = jQuery;
    const el = $('#SellerShowCase_topSkillsList');
    const skills = ${JSON.stringify(skills)};

    // Method 1: Use select2("data", [...])
    try {
      el.select2("data", skills);
      const currentData = el.select2("data");
      return 'Method 1 (data): set ' + currentData.length + ' skills: ' + currentData.map(d => d.text).join(', ');
    } catch(e) {
      return 'Method 1 failed: ' + e.message;
    }
  `);
  console.log(r);

  // Verify skills were added
  r = await eval_(`
    const $ = jQuery;
    const data = $('#SellerShowCase_topSkillsList').select2("data");
    const val = $('#SellerShowCase_topSkillsList').val();
    const chips = Array.from(document.querySelectorAll('.select2-search-choice'))
      .map(c => c.textContent.replace(/×/g, '').trim())
      .filter(t => t.length > 0);
    return JSON.stringify({ dataCount: data?.length, dataTexts: data?.map(d => d.text), val, chips });
  `);
  console.log("Verification:", r);

  // Step 3: Add Language - English
  console.log("\n=== 3. Adding Language: English ===");
  r = await eval_(`
    return new Promise((resolve) => {
      const $ = jQuery;
      $.ajax({
        url: '/member/LanguagesAutocomplete',
        data: { term: 'English' },
        dataType: 'json',
        success: function(data) { resolve(JSON.stringify(data)); },
        error: function(xhr, status, err) { resolve('error: ' + err); }
      });
    });
  `);
  console.log("Language search:", r);

  const languages = JSON.parse(r);
  if (Array.isArray(languages) && languages.length > 0) {
    const english = languages.find(l => l.text === 'English') || languages[0];
    console.log(`Found: ${english.id} = "${english.text}"`);

    r = await eval_(`
      const $ = jQuery;
      const el = $('#SellerShowCase_languagesString');
      try {
        el.select2("data", [${JSON.stringify(english)}]);
        const currentData = el.select2("data");
        return 'Set language: ' + currentData.map(d => d.text).join(', ');
      } catch(e) {
        return 'Failed: ' + e.message;
      }
    `);
    console.log(r);
  }

  // Step 4: Fix About text (was cleared)
  console.log("\n=== 4. Fixing About text ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_about');
    if (!el) return 'not found';
    const current = el.value;
    if (current.length < 10) {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(el, 'Professional writer and data specialist with AI-enhanced workflows. I deliver high-quality content, data processing, and research with fast turnaround. Services include article writing, blog posts, technical writing, data entry, Excel spreadsheet work, research reports, copywriting, editing, and proofreading. I combine deep expertise with modern AI tools for faster delivery and exceptional quality. Based in Seattle, available for projects worldwide.');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'Set about text (' + el.value.length + ' chars)';
    }
    return 'Already has text (' + current.length + ' chars)';
  `);
  console.log(r);

  // Step 5: Upload profile photo
  console.log("\n=== 5. Profile Photo ===");
  r = await eval_(`
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      return JSON.stringify({
        name: fileInput.name,
        id: fileInput.id,
        accept: fileInput.accept,
        multiple: fileInput.multiple
      });
    }
    return 'no file input found';
  `);
  console.log("File input:", r);

  // Step 6: Final form state
  console.log("\n=== 6. Final Form State ===");
  r = await eval_(`
    const $ = jQuery;
    return JSON.stringify({
      jobTitle: document.getElementById('MemberProfile_job_title')?.value,
      about: (document.getElementById('MemberProfile_about')?.value || '').substring(0, 80) + '...',
      location: document.querySelector('input[name="location_combo"]')?.value,
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value,
      skillsData: $('#SellerShowCase_topSkillsList').select2('data')?.map(d => d.text),
      skillsVal: $('#SellerShowCase_topSkillsList').val(),
      languagesData: $('#SellerShowCase_languagesString').select2('data')?.map(d => d.text),
      languagesVal: $('#SellerShowCase_languagesString').val(),
      chips: Array.from(document.querySelectorAll('.select2-search-choice')).map(c => c.textContent.replace(/×/g, '').trim()).filter(t => t.length > 0)
    });
  `);
  console.log(r);

  const finalState = JSON.parse(r);

  // Step 7: Submit if everything looks good
  if (finalState.jobTitle && finalState.skillsData?.length > 0 && finalState.languagesData?.length > 0 && finalState.rate) {
    console.log("\n=== 7. Submitting Application ===");
    r = await eval_(`
      const btn = document.querySelector('button[type="submit"], input[type="submit"]');
      if (btn && !btn.disabled) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent?.trim() || btn.value });
      }
      return null;
    `);

    if (r) {
      const pos = JSON.parse(r);
      console.log(`Clicking "${pos.text}"...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(5000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          preview: document.body.innerText.substring(0, 1500),
          errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 100))
            .filter(t => t.length > 3)
        });
      `);
      console.log("Submit result:", r);
    }
  } else {
    console.log("\nMissing fields - cannot submit:");
    if (!finalState.jobTitle) console.log("  - Job title");
    if (!finalState.skillsData?.length) console.log("  - Skills");
    if (!finalState.languagesData?.length) console.log("  - Languages");
    if (!finalState.rate) console.log("  - Rate");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
