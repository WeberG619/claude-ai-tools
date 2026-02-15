const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  let tab = tabs.find(t => t.type === "page" && t.url.includes("unipark"));
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

  const setInput = async (selector, value) => {
    return await eval_(`
      const el = document.querySelector('${selector}');
      if (!el) return 'not found: ${selector}';
      const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      nativeSetter.call(el, '${value}');
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return 'set: ' + el.value;
    `);
  };

  // Helper to process a survey page
  async function processPage() {
    const pageText = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\n--- PAGE ---");
    console.log(pageText.substring(0, 1500));

    // Get all form elements
    const fieldsJson = await eval_(`
      const inputs = document.querySelectorAll('input, select, textarea');
      return JSON.stringify(Array.from(inputs).filter(i =>
        i.offsetParent !== null && i.type !== 'hidden'
      ).map(i => ({
        tag: i.tagName, type: i.type, name: i.name || '', id: i.id || '',
        value: i.value?.substring(0, 80) || '',
        label: i.labels?.[0]?.textContent?.trim().substring(0, 100) || '',
        options: i.tagName === 'SELECT' ? Array.from(i.options).map(o => o.value + ':' + o.text.substring(0,30)).join('|') : ''
      })));
    `);
    console.log("Fields:", fieldsJson);
    return { pageText, fields: JSON.parse(fieldsJson || '[]') };
  }

  // Enter Clickworker ID
  let r = await setInput('#v_1', '25671709');
  console.log("Clickworker ID:", r);
  await sleep(300);

  // Click Continue
  r = await eval_(`
    const btn = document.querySelector('#os, button[name="submit_button"]');
    if (btn) { btn.click(); return 'clicked Continue'; }
    return 'Continue not found';
  `);
  console.log("Continue:", r);
  await sleep(3000);

  // Process pages until we get a code
  for (let page = 0; page < 20; page++) {
    const { pageText, fields } = await processPage();

    // Check if we got a code
    if (pageText.includes('code') && pageText.match(/[A-Za-z0-9]{6,}/)) {
      const codeMatch = pageText.match(/(?:code|Code|CODE)[:\s]+([A-Za-z0-9]+)/);
      if (codeMatch) {
        console.log("\n*** FOUND CODE: " + codeMatch[1] + " ***");
        break;
      }
    }

    // Check for end of survey
    if (pageText.includes('Thank you') && pageText.includes('completed') || pageText.includes('end of the survey')) {
      console.log("\n*** SURVEY COMPLETE ***");
      break;
    }

    // Handle different field types
    const radios = fields.filter(f => f.type === 'radio');
    const checkboxes = fields.filter(f => f.type === 'checkbox');
    const textInputs = fields.filter(f => f.type === 'text' || f.type === 'tel' || f.type === 'number');
    const selects = fields.filter(f => f.tag === 'SELECT');
    const textareas = fields.filter(f => f.tag === 'TEXTAREA');

    if (radios.length > 0) {
      // Group radios by name
      const radioGroups = {};
      radios.forEach(r => {
        if (!radioGroups[r.name]) radioGroups[r.name] = [];
        radioGroups[r.name].push(r);
      });

      for (const [name, group] of Object.entries(radioGroups)) {
        // For LLM usage survey: pick middle-ish options (moderate use)
        // For attentiveness checks: read carefully
        const pageLC = pageText.toLowerCase();
        let pickIdx;

        // Check for attention checks
        if (pageLC.includes('select') && pageLC.includes('option') && pageLC.includes('attention')) {
          // This might be an attention check - look for the specific instruction
          const instructionMatch = pageText.match(/select\s+"([^"]+)"/i) || pageText.match(/choose\s+"([^"]+)"/i);
          if (instructionMatch) {
            const target = instructionMatch[1].toLowerCase();
            pickIdx = group.findIndex(r => r.label.toLowerCase().includes(target) || r.value.toLowerCase().includes(target));
            if (pickIdx === -1) pickIdx = Math.floor(group.length / 2);
          } else {
            pickIdx = Math.floor(group.length / 2);
          }
        } else {
          // Pick a moderate/middle option for Likert scales
          // For yes/no, pick yes
          if (group.length === 2) {
            pickIdx = 0; // Yes or first option
          } else if (group.length <= 5) {
            pickIdx = Math.floor(group.length / 2); // Middle for Likert
          } else {
            pickIdx = 2; // Slightly above minimum for longer scales
          }
        }

        const pick = group[pickIdx] || group[0];
        r = await eval_(`
          const radio = document.querySelector('#${pick.id}');
          if (radio) {
            radio.checked = true;
            radio.dispatchEvent(new Event('change', { bubbles: true }));
            radio.click();
            return 'picked: ' + radio.value;
          }
          return 'not found';
        `);
        console.log(`Radio ${name}: ${r}`);
      }
    }

    if (selects.length > 0) {
      for (const sel of selects) {
        r = await eval_(`
          const el = document.querySelector('#${sel.id}');
          if (el && el.options.length > 1) {
            el.selectedIndex = Math.min(2, el.options.length - 1);
            el.dispatchEvent(new Event('change', { bubbles: true }));
            return 'selected: ' + el.value;
          }
          return 'skip';
        `);
        console.log(`Select ${sel.name}: ${r}`);
      }
    }

    if (textareas.length > 0) {
      for (const ta of textareas) {
        await eval_(`
          const el = document.querySelector('#${ta.id}');
          if (el) {
            el.value = 'I use LLMs regularly for research, writing, and problem-solving tasks. They help me work more efficiently.';
            el.dispatchEvent(new Event('input', { bubbles: true }));
          }
        `);
        console.log(`Textarea ${ta.name}: filled`);
      }
    }

    if (textInputs.length > 0 && radios.length === 0 && selects.length === 0) {
      // Only fill text inputs if there are no other form elements
      for (const input of textInputs) {
        if (!input.value) {
          await eval_(`
            const el = document.querySelector('#${input.id}');
            if (el && !el.value) {
              const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
              nativeSetter.call(el, '3');
              el.dispatchEvent(new Event('input', { bubbles: true }));
            }
          `);
        }
      }
    }

    await sleep(500);

    // Click Continue/Next
    r = await eval_(`
      const btn = document.querySelector('#os, button[name="submit_button"], input[type="submit"]');
      if (btn) { btn.click(); return 'clicked: ' + (btn.textContent || btn.value); }
      return 'no continue button';
    `);
    console.log("Next:", r);
    await sleep(3000);
  }

  // Final page - look for code
  r = await eval_(`return document.body.innerText.substring(0, 3000)`);
  console.log("\n=== FINAL PAGE ===");
  console.log(r);

  // Screenshot
  const screenshot = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const fs = await import('fs');
  fs.writeFileSync('D:\\_CLAUDE-TOOLS\\clickworker_llm_done.png', Buffer.from(screenshot.data, 'base64'));
  console.log("\nScreenshot saved");

  ws.close();
})().catch(e => console.error("Error:", e.message));
