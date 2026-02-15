// Fill all PPH fields and submit - complete in one shot
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
  const photoPath = "D:\\_CLAUDE-TOOLS\\weber_profile_photo.jpg";
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected\n");

  await send("DOM.enable");
  await send("Page.enable");

  // Step 1: Upload photo first
  console.log("=== 1. Uploading Photo ===");
  let r = await eval_(`
    return (document.body?.innerText || '').includes('upload at least') ? 'needs upload' : 'no upload error';
  `);
  console.log("Photo status:", r);

  if (r === 'needs upload') {
    const docResult = await send("DOM.getDocument");
    const searchResult = await send("DOM.querySelectorAll", {
      nodeId: docResult.root.nodeId,
      selector: 'input[type="file"]'
    });
    if (searchResult.nodeIds?.length) {
      await send("DOM.setFileInputFiles", {
        nodeId: searchResult.nodeIds[0],
        files: [photoPath]
      });
      await eval_(`
        const fi = document.querySelector('input[type="file"]');
        if (fi) fi.dispatchEvent(new Event('change', { bubbles: true }));
      `);
      console.log("Photo uploaded");
      await sleep(2000);
    }
  }

  // Step 2: Set Job Title
  console.log("\n=== 2. Setting Job Title ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_job_title');
    if (!el) return 'not found';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, 'Writer & Data Specialist');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'Set: ' + el.value;
  `);
  console.log(r);

  // Step 3: Set About
  console.log("\n=== 3. Setting About ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_about');
    if (!el) return 'not found';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
    setter.call(el, 'Professional writer and data specialist with AI-enhanced workflows. I deliver high-quality content, data processing, and research with fast turnaround. Services include article writing, blog posts, technical writing, data entry, Excel spreadsheet work, research reports, copywriting, editing, and proofreading. I combine deep expertise with modern AI tools for faster delivery and exceptional quality. Based in Seattle, available for projects worldwide.');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'Set (' + el.value.length + ' chars)';
  `);
  console.log(r);

  // Step 4: Set Rate
  console.log("\n=== 4. Setting Rate ===");
  r = await eval_(`
    const el = document.getElementById('MemberProfile_real_hour_rate');
    if (!el) return 'not found';
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(el, '28');
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    return 'Set: ' + el.value;
  `);
  console.log(r);

  // Step 5: Add Skills via AJAX + Select2
  console.log("\n=== 5. Adding Skills ===");
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

  // Step 6: Add Language
  console.log("\n=== 6. Adding Language ===");
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
              resolve('Set: ' + current.map(d => d.text).join(', '));
            } catch(e) { resolve('Error: ' + e.message); }
          } else { resolve('No languages found'); }
        },
        error: function(xhr, status, err) { resolve('AJAX error: ' + err); }
      });
    });
  `);
  console.log(r);

  // Step 7: Verify everything
  console.log("\n=== 7. FINAL VERIFICATION ===");
  r = await eval_(`
    const $ = jQuery;
    return JSON.stringify({
      photoOk: !(document.body?.innerText || '').includes('upload at least'),
      jobTitle: document.getElementById('MemberProfile_job_title')?.value || '',
      aboutLen: (document.getElementById('MemberProfile_about')?.value || '').length,
      location: document.querySelector('input[name="location_combo"]')?.value || '',
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value || '',
      skills: (() => { try { return ($('#SellerShowCase_topSkillsList').select2('data') || []).map(d => d.text); } catch(e) { return []; } })(),
      languages: (() => { try { return ($('#SellerShowCase_languagesString').select2('data') || []).map(d => d.text); } catch(e) { return []; } })(),
      errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3)
    });
  `);
  const state = JSON.parse(r);
  console.log("Photo OK:", state.photoOk);
  console.log("Job Title:", state.jobTitle);
  console.log("About:", state.aboutLen, "chars");
  console.log("Location:", state.location);
  console.log("Rate: £" + state.rate);
  console.log("Skills:", state.skills.join(", "), `(${state.skills.length})`);
  console.log("Languages:", state.languages.join(", "));
  console.log("Errors:", state.errors);

  // Step 8: Submit
  const ready = state.photoOk && state.jobTitle && state.aboutLen > 50 &&
                state.rate && state.skills.length > 0 && state.languages.length > 0;

  if (ready) {
    console.log("\n=== 8. SUBMITTING ===");
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
      const btn = JSON.parse(r);
      console.log(`Clicking "${btn.text}"...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btn.x, y: btn.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btn.x, y: btn.y, button: "left", clickCount: 1 });
      await sleep(8000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 150))
            .filter(t => t.length > 3),
          preview: document.body?.innerText?.substring(0, 1500)
        });
      `);
      console.log("\nResult:", r);
    }
  } else {
    console.log("\nNOT READY:");
    if (!state.photoOk) console.log("  - Photo required");
    if (!state.jobTitle) console.log("  - Job title empty");
    if (state.aboutLen < 50) console.log("  - About too short");
    if (!state.rate) console.log("  - Rate empty");
    if (state.skills.length === 0) console.log("  - No skills");
    if (state.languages.length === 0) console.log("  - No languages");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
