// Upwork profile steps 4-10: Title, Experience, Education, Languages, Bio, Rate, Photo, etc.
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found`);
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function getPageState(eval_) {
  const r = await eval_(`
    const url = location.href;
    const step = url.split('/').pop().split('?')[0];
    const body = document.body.innerText.substring(0, 800);
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        id: el.id, type: el.type, tag: el.tagName,
        placeholder: (el.placeholder || '').substring(0, 50),
        label: (el.labels && el.labels[0] ? el.labels[0].textContent.trim() : el.getAttribute('aria-label') || '').substring(0, 50),
        value: el.value.substring(0, 30),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    const btns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50)
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify({ url, step, body, inputs, btns });
  `);
  return JSON.parse(r);
}

async function findAndClickButton(send, eval_, textMatch) {
  const r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, a[role="button"], [role="button"]'))
      .find(b => b.textContent.trim().includes('${textMatch}') && b.offsetParent !== null && !b.textContent.trim().includes('Skip to content'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found' });
  `);
  const btn = JSON.parse(r);
  if (!btn.error) {
    await sleep(300);
    await clickAt(send, btn.x, btn.y);
    return true;
  }
  return false;
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  for (let iteration = 0; iteration < 15; iteration++) {
    const state = await getPageState(eval_);
    console.log(`\n=== Step: ${state.step} ===`);
    console.log(`Inputs: ${state.inputs.length}, Buttons: ${state.btns.map(b => b.text).join(' | ')}`);
    console.log(`Body: ${state.body.substring(0, 250)}`);

    // Check if done
    if (state.url.includes('dashboard') || state.url.includes('best-matches') || state.url.includes('feed') ||
        state.body.includes('profile is ready') || state.body.includes('Looking good') || state.body.includes('Your profile')) {
      console.log("\n*** PROFILE COMPLETE ***");
      break;
    }

    const step = state.step;

    if (step === 'title' || state.body.includes('add a title')) {
      // Set professional title
      const titleInput = state.inputs.find(i => i.tag !== 'TEXTAREA') || state.inputs[0];
      if (titleInput) {
        await clickAt(send, titleInput.x, titleInput.y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(100);
        await send("Input.insertText", { text: "BIM Specialist | Technical Writer | Data Entry Expert" });
        console.log("Title set");
        await sleep(500);
      }
    } else if (step === 'experience' || step === 'employment' || state.body.includes('work experience') || state.body.includes('add your experience')) {
      // Check for experience level radio or skip
      const r = await eval_(`
        const radios = Array.from(document.querySelectorAll('input[type="radio"]'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            value: el.value, checked: el.checked,
            label: (el.closest('label') ? el.closest('label').textContent.trim() : '').substring(0, 50),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + 10)
          }));
        return JSON.stringify(radios);
      `);
      const radios = JSON.parse(r);
      console.log("Radios:", radios.length);
      if (radios.length > 0) {
        // Select middle option (some experience)
        const mid = radios.length > 1 ? radios[1] : radios[0];
        await clickAt(send, mid.x, mid.y);
        console.log(`Selected: ${mid.label}`);
        await sleep(500);
      }
      // Skip adding employment for now
    } else if (step === 'education' || state.body.includes('education')) {
      // Skip education
      console.log("Skipping education");
    } else if (step === 'languages' || state.body.includes('language')) {
      // Check if English is already set
      console.log("Languages step - English should be default");
      // Check for proficiency dropdown
      const r = await eval_(`
        const selects = Array.from(document.querySelectorAll('select'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            id: el.id, value: el.value,
            options: Array.from(el.options).map(o => o.text).join(', '),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));
        return JSON.stringify(selects);
      `);
      console.log("Selects:", r);
    } else if (step === 'overview' || step === 'bio' || state.body.includes('bio') || state.body.includes('overview') || state.body.includes('describe yourself')) {
      const textarea = state.inputs.find(i => i.tag === 'TEXTAREA');
      if (textarea) {
        await clickAt(send, textarea.x, textarea.y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
        await sleep(100);
        await send("Input.insertText", { text: "Experienced BIM specialist and technical professional with expertise in Revit, AutoCAD, and building information modeling. I offer high-quality writing, data entry, and document management services. Detail-oriented with a strong commitment to accuracy and timely delivery. Skilled in creating professional resumes, technical documents, and business content. Whether you need meticulous data entry, polished writing, or BIM/CAD drafting services, I deliver consistent, professional results." });
        console.log("Bio set");
        await sleep(500);
      }
    } else if (step === 'rate' || state.body.includes('hourly rate') || state.body.includes('per hour')) {
      if (state.inputs.length > 0) {
        const rateInput = state.inputs[0];
        await clickAt(send, rateInput.x, rateInput.y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await sleep(50);
        await send("Input.insertText", { text: "25" });
        console.log("Rate: $25/hr");
        await sleep(500);
      }
    } else if (step === 'photo' || state.body.includes('profile photo') || state.body.includes('photo')) {
      console.log("Photo step - skipping");
    } else if (step === 'location' || state.body.includes('location') || state.body.includes('city')) {
      if (state.inputs.length > 0) {
        await clickAt(send, state.inputs[0].x, state.inputs[0].y);
        await sleep(200);
        await send("Input.insertText", { text: "Los Angeles" });
        await sleep(2000);
        const r = await eval_(`
          const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
          return JSON.stringify(opts.slice(0, 3));
        `);
        const opts = JSON.parse(r);
        if (opts.length > 0) {
          await clickAt(send, opts[0].x, opts[0].y);
          console.log(`Location: ${opts[0].text}`);
        }
      }
    } else if (step === 'review' || state.body.includes('review')) {
      console.log("Review step - submitting profile");
    }

    // Navigate: Next > Skip > Submit > Review
    await sleep(500);
    let advanced = false;

    // Try Next variants
    for (const txt of ['Next,', 'Next', 'Review your profile', 'Submit profile', 'Submit', 'Continue']) {
      if (!advanced) {
        advanced = await findAndClickButton(send, eval_, txt);
        if (advanced) {
          console.log(`Clicked: ${txt}`);
          break;
        }
      }
    }
    if (!advanced) {
      // Try Skip
      const r = await eval_(`
        const skipBtn = Array.from(document.querySelectorAll('button, a'))
          .find(b => b.textContent.trim().includes('Skip') && !b.textContent.trim().includes('Skip to content') && b.offsetParent !== null);
        if (skipBtn) {
          const rect = skipBtn.getBoundingClientRect();
          return JSON.stringify({ text: skipBtn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'no skip' });
      `);
      const skip = JSON.parse(r);
      if (!skip.error) {
        await clickAt(send, skip.x, skip.y);
        advanced = true;
        console.log(`Clicked: ${skip.text}`);
      }
    }

    if (!advanced) {
      console.log("No navigation button found");
      break;
    }

    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
