// Review PPH application state and submit
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

  // Step 1: Full state check
  console.log("=== CURRENT APPLICATION STATE ===");
  let r = await eval_(`
    const $ = jQuery;
    return JSON.stringify({
      url: location.href,
      jobTitle: document.getElementById('MemberProfile_job_title')?.value || '',
      about: document.getElementById('MemberProfile_about')?.value || '',
      location: document.querySelector('input[name="location_combo"]')?.value || '',
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value || '',
      currency: document.getElementById('MemberProfile_real_hour_rate_currency')?.value || '',
      skillsData: (() => {
        try { return $('#SellerShowCase_topSkillsList').select2('data')?.map(d => d.text) || []; }
        catch(e) { return []; }
      })(),
      skillsVal: $('#SellerShowCase_topSkillsList').val() || '',
      languagesData: (() => {
        try { return $('#SellerShowCase_languagesString').select2('data')?.map(d => d.text) || []; }
        catch(e) { return []; }
      })(),
      languagesVal: $('#SellerShowCase_languagesString').val() || '',
      skillChips: Array.from(document.querySelectorAll('.select2-search-choice'))
        .map(c => c.textContent.replace(/×/g, '').trim())
        .filter(t => t.length > 0),
      hasPhoto: !!document.querySelector('.profile-photo img, [class*="ProfilePhoto"] img, .plupload_file_name'),
      photoDropzone: !!document.querySelector('.plupload, [class*="upload"], [class*="dropzone"]'),
      submitBtn: (() => {
        const btn = document.querySelector('button[type="submit"], input[type="submit"]');
        return btn ? { text: btn.textContent?.trim() || btn.value, disabled: btn.disabled } : null;
      })(),
      errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3),
      emailVerified: !(document.body?.innerText || '').includes('check your inbox')
    });
  `);

  const state = JSON.parse(r);
  console.log("URL:", state.url);
  console.log("Job Title:", JSON.stringify(state.jobTitle));
  console.log("About:", state.about.substring(0, 100) + (state.about.length > 100 ? '...' : ''));
  console.log("About length:", state.about.length);
  console.log("Location:", state.location);
  console.log("Rate:", state.rate, state.currency);
  console.log("Skills (data):", state.skillsData);
  console.log("Skills (val):", state.skillsVal);
  console.log("Languages (data):", state.languagesData);
  console.log("Languages (val):", state.languagesVal);
  console.log("Chips visible:", state.skillChips);
  console.log("Has photo:", state.hasPhoto);
  console.log("Submit button:", state.submitBtn);
  console.log("Errors:", state.errors);
  console.log("Email verified:", state.emailVerified);

  // Check what's missing
  const issues = [];
  if (!state.jobTitle) issues.push("Job title empty");
  if (state.about.length < 50) issues.push("About text too short or empty");
  if (!state.rate || state.rate === '0') issues.push("Rate empty");
  if (state.skillsData.length === 0 && state.skillChips.length === 0) issues.push("No skills");
  if (state.languagesData.length === 0) issues.push("No languages");

  if (issues.length > 0) {
    console.log("\n=== ISSUES FOUND - FIXING ===");
    issues.forEach(i => console.log("  -", i));

    // Fix job title if needed
    if (!state.jobTitle) {
      console.log("\nFixing job title...");
      r = await eval_(`
        const el = document.getElementById('MemberProfile_job_title');
        if (el) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(el, 'Writer & Data Specialist');
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set: ' + el.value;
        }
        return 'not found';
      `);
      console.log(r);
    }

    // Fix about if needed
    if (state.about.length < 50) {
      console.log("\nFixing about text...");
      r = await eval_(`
        const el = document.getElementById('MemberProfile_about');
        if (el) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
          setter.call(el, 'Professional writer and data specialist with AI-enhanced workflows. I deliver high-quality content, data processing, and research with fast turnaround. Services include article writing, blog posts, technical writing, data entry, Excel spreadsheet work, research reports, copywriting, editing, and proofreading. I combine deep expertise with modern AI tools for faster delivery and exceptional quality. Based in Seattle, available for projects worldwide.');
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set (' + el.value.length + ' chars)';
        }
        return 'not found';
      `);
      console.log(r);
    }

    // Fix rate if needed
    if (!state.rate || state.rate === '0') {
      console.log("\nFixing rate...");
      r = await eval_(`
        const el = document.getElementById('MemberProfile_real_hour_rate');
        if (el) {
          const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
          setter.call(el, '28');
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          return 'Set: ' + el.value;
        }
        return 'not found';
      `);
      console.log(r);
    }

    // Fix skills if needed
    if (state.skillsData.length === 0 && state.skillChips.length === 0) {
      console.log("\nFixing skills via AJAX + Select2...");
      const skillQueries = [
        'Data entry', 'Excel', 'Content Writing', 'Copywriting',
        'Article Writing', 'Research', 'Technical Writing', 'Proofreading',
        'Transcription', 'Blog Writing', 'Report Writing', 'Editing'
      ];

      r = await eval_(`
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
              if (data && data.length > 0) {
                const exact = data.find(d => d.text.toLowerCase() === q.toLowerCase()) || data[0];
                skillIds.push({ id: exact.id, text: exact.text });
              }
            } catch(e) {}
          }
          // Set via Select2 API
          try {
            $('#SellerShowCase_topSkillsList').select2('data', skillIds);
            const current = $('#SellerShowCase_topSkillsList').select2('data');
            resolve('Set ' + current.length + ' skills: ' + current.map(d => d.text).join(', '));
          } catch(e) {
            resolve('Error: ' + e.message);
          }
        });
      `);
      console.log(r);
    }

    // Fix languages if needed
    if (state.languagesData.length === 0) {
      console.log("\nFixing language...");
      r = await eval_(`
        return new Promise((resolve) => {
          const $ = jQuery;
          $.ajax({
            url: '/member/LanguagesAutocomplete',
            data: { term: 'English' },
            dataType: 'json',
            success: function(data) {
              if (data && data.length > 0) {
                const english = data.find(l => l.text === 'English') || data[0];
                try {
                  $('#SellerShowCase_languagesString').select2('data', [english]);
                  const current = $('#SellerShowCase_languagesString').select2('data');
                  resolve('Set language: ' + current.map(d => d.text).join(', '));
                } catch(e) {
                  resolve('Error: ' + e.message);
                }
              } else {
                resolve('No languages found');
              }
            },
            error: function(xhr, status, err) { resolve('AJAX error: ' + err); }
          });
        });
      `);
      console.log(r);
    }
  }

  // Step 2: Final verification
  console.log("\n=== FINAL VERIFICATION ===");
  r = await eval_(`
    const $ = jQuery;
    return JSON.stringify({
      jobTitle: document.getElementById('MemberProfile_job_title')?.value || '',
      aboutLen: (document.getElementById('MemberProfile_about')?.value || '').length,
      aboutPreview: (document.getElementById('MemberProfile_about')?.value || '').substring(0, 80),
      location: document.querySelector('input[name="location_combo"]')?.value || '',
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value || '',
      skillCount: (() => {
        try { return ($('#SellerShowCase_topSkillsList').select2('data') || []).length; }
        catch(e) { return 0; }
      })(),
      skills: (() => {
        try { return ($('#SellerShowCase_topSkillsList').select2('data') || []).map(d => d.text); }
        catch(e) { return []; }
      })(),
      languages: (() => {
        try { return ($('#SellerShowCase_languagesString').select2('data') || []).map(d => d.text); }
        catch(e) { return []; }
      })(),
      chips: Array.from(document.querySelectorAll('.select2-search-choice'))
        .map(c => c.textContent.replace(/×/g, '').trim())
        .filter(t => t.length > 0),
      errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
        .map(el => el.textContent.trim().substring(0, 100))
    });
  `);

  const finalState = JSON.parse(r);
  console.log("Job Title:", finalState.jobTitle);
  console.log("About:", finalState.aboutPreview + "... (" + finalState.aboutLen + " chars)");
  console.log("Location:", finalState.location);
  console.log("Rate:", finalState.rate);
  console.log("Skills:", finalState.skills.join(", ") + " (" + finalState.skillCount + ")");
  console.log("Languages:", finalState.languages.join(", "));
  console.log("Chips:", finalState.chips.join(", "));
  console.log("Errors:", finalState.errors);

  // Step 3: Submit
  const ready = finalState.jobTitle && finalState.aboutLen > 50 && finalState.rate &&
                finalState.skillCount > 0 && finalState.languages.length > 0;

  if (ready) {
    console.log("\n=== SUBMITTING APPLICATION ===");
    r = await eval_(`
      const btn = document.querySelector('button[type="submit"], input[type="submit"]');
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        return JSON.stringify({
          text: btn.textContent?.trim() || btn.value,
          disabled: btn.disabled,
          rect: { x: btn.getBoundingClientRect().x + btn.getBoundingClientRect().width/2,
                  y: btn.getBoundingClientRect().y + btn.getBoundingClientRect().height/2 }
        });
      }
      return null;
    `);
    console.log("Submit button:", r);

    if (r) {
      const btn = JSON.parse(r);
      if (!btn.disabled) {
        console.log(`Clicking "${btn.text}"...`);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btn.rect.x, y: btn.rect.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btn.rect.x, y: btn.rect.y, button: "left", clickCount: 1 });
        await sleep(8000);

        // Check result
        r = await eval_(`
          return JSON.stringify({
            url: location.href,
            bodyPreview: document.body?.innerText?.substring(0, 2000),
            errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
              .filter(el => el.offsetParent !== null)
              .map(el => el.textContent.trim().substring(0, 150))
              .filter(t => t.length > 3)
          });
        `);
        console.log("\nSubmit result:", r);
      } else {
        console.log("Submit button is disabled!");
      }
    }
  } else {
    console.log("\nNOT READY - missing fields:");
    if (!finalState.jobTitle) console.log("  - Job title");
    if (finalState.aboutLen < 50) console.log("  - About text");
    if (!finalState.rate) console.log("  - Rate");
    if (finalState.skillCount === 0) console.log("  - Skills");
    if (finalState.languages.length === 0) console.log("  - Languages");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
