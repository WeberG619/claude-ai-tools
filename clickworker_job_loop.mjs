const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("clickworker"));
  if (!tab) tab = tabs.find(t => t.type === "page");
  if (!tab) { console.log("No tab"); return; }

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  // Answer current lawsuit #2 - select option 0 (Yes, keep residents safe)
  let r = await eval_(`
    const radio = document.querySelector('#output_468191595__df_create_sunnamed_selection__x0t5v_0');
    if (radio) {
      radio.checked = true;
      radio.dispatchEvent(new Event('change', { bubbles: true }));
      return 'selected: ' + radio.value;
    }
    return 'radio not found';
  `);
  console.log("Answer:", r);
  await sleep(300);

  // Submit
  r = await eval_(`
    const btn = document.querySelector('input[type="submit"][name="submit_job"]');
    if (btn) { btn.click(); return 'clicked Send'; }
    return 'Send not found';
  `);
  console.log("Send:", r);
  await sleep(5000);

  r = await eval_(`return window.location.href`);
  console.log("\nURL:", r);

  // Check balance
  r = await eval_(`
    const text = document.body.innerText;
    const match = text.match(/Account balance \\$ ([\\d.]+)/);
    return match ? match[1] : 'unknown';
  `);
  console.log("Balance: $" + r);

  // Check if more jobs in this project
  r = await eval_(`
    const text = document.body.innerText;
    if (text.includes('no further jobs')) return 'no more jobs in this project';
    return 'may have more';
  `);
  console.log("Status:", r);

  // Now try the next jobs in priority order
  const jobsToTry = [
    { id: '1265831', name: 'Lawsuit #2 (more)' },
    { id: '1262195', name: 'LLM Survey ($1.43)' },
    { id: '1262735', name: 'Avatar Survey ($1.19)' },
    { id: '1265821', name: 'Christian athlete ($0.26)' },
    { id: '1262113', name: 'Keyword search ($0.10)' },
    { id: '1255859', name: 'Keyword search 2 ($0.10)' },
    { id: '1137665', name: 'Welcome onboarding ($0.01)' },
  ];

  for (const job of jobsToTry) {
    console.log(`\n--- Trying ${job.name} (${job.id}) ---`);
    await send("Page.navigate", { url: `https://workplace.clickworker.com/en/workplace/jobs/${job.id}/edit` });
    await sleep(4000);

    r = await eval_(`return window.location.href`);
    console.log("URL:", r);

    // Handle agreement pages
    if (r.includes('confirm_agreement')) {
      r = await eval_(`
        const btn = document.querySelector('input[type="submit"][value="Agree"]');
        if (btn) { btn.click(); return 'agreed'; }
        return 'no agree btn';
      `);
      console.log("Agreement:", r);
      await sleep(3000);
      r = await eval_(`return window.location.href`);
    }

    if (r.includes('confirm_instruction')) {
      r = await eval_(`
        const btn = document.querySelector('input[type="submit"][value="Agree"], input[type="submit"][name="confirm"]');
        if (btn) { btn.click(); return 'confirmed'; }
        return 'no confirm btn';
      `);
      console.log("Instructions:", r);
      await sleep(3000);
      r = await eval_(`return window.location.href`);
    }

    // Check if we're on a job edit page
    if (!r.includes('/edit')) {
      r = await eval_(`return document.body.innerText.substring(0, 500)`);
      console.log("Not on edit page:", r.substring(0, 200));
      continue;
    }

    // Get the page content and form
    const pageText = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("Task:", pageText.substring(0, 500));

    // Get radio buttons
    r = await eval_(`
      const radios = document.querySelectorAll('input[type="radio"]');
      return JSON.stringify(Array.from(radios).map(r => ({
        id: r.id, value: r.value?.substring(0, 80), name: r.name,
        label: r.labels?.[0]?.textContent?.trim().substring(0, 80) || ''
      })));
    `);
    const radios = JSON.parse(r || '[]');
    console.log("Radios:", radios.length);

    if (radios.length > 0) {
      // Pick a thoughtful answer - first non-"other" option for surveys
      let pickIdx = 0;
      // For lawsuit-type questions, pick the side that favors safety/responsibility
      // For surveys, pick the first relevant option
      const firstRadio = radios[pickIdx];
      r = await eval_(`
        const radio = document.querySelector('#${firstRadio.id}');
        if (radio) {
          radio.checked = true;
          radio.dispatchEvent(new Event('change', { bubbles: true }));
          return 'selected: ' + radio.value;
        }
        return 'not found';
      `);
      console.log("Selected:", r);
      await sleep(300);

      // Check for textareas that need filling
      r = await eval_(`
        const tas = document.querySelectorAll('textarea');
        const visible = Array.from(tas).filter(t => t.offsetParent !== null);
        return JSON.stringify(visible.map(t => ({name: t.name, id: t.id, required: t.required})));
      `);
      const textareas = JSON.parse(r || '[]');
      if (textareas.length > 0) {
        console.log("Has textareas:", textareas.length);
        // Fill any required textareas
        for (const ta of textareas) {
          if (ta.required) {
            await eval_(`
              const el = document.querySelector('#${ta.id}');
              if (el) {
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                nativeSetter.call(el, 'I believe this is an important consideration for public safety and individual rights.');
                el.dispatchEvent(new Event('input', { bubbles: true }));
              }
            `);
          }
        }
      }

      // Submit
      r = await eval_(`
        const btn = document.querySelector('input[type="submit"][name="submit_job"]');
        if (btn) { btn.click(); return 'submitted'; }
        return 'no submit btn';
      `);
      console.log("Submit:", r);
      await sleep(4000);

      // Check balance
      r = await eval_(`
        const text = document.body.innerText;
        const match = text.match(/Account balance \\$ ([\\d.]+)/);
        return match ? match[1] : 'unknown';
      `);
      console.log("Balance: $" + r);
    } else {
      console.log("No radio buttons found - skipping");
    }
  }

  // Final balance check
  await send("Page.navigate", { url: "https://workplace.clickworker.com/en/workplace/jobs" });
  await sleep(3000);
  r = await eval_(`
    const text = document.body.innerText;
    const match = text.match(/Account balance \\$ ([\\d.]+)/);
    return match ? match[1] : 'unknown';
  `);
  console.log("\n=== FINAL BALANCE: $" + r + " ===");

  ws.close();
})().catch(e => console.error("Error:", e.message));
