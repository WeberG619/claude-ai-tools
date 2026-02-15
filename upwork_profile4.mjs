// Upwork profile - click Fill out manually and proceed through all 10 steps
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

async function findAndClickButton(send, eval_, textMatch) {
  const r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button, a[role="button"], [role="button"]'))
      .find(b => b.textContent.trim().includes('${textMatch}') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'not found: ${textMatch}' });
  `);
  const btn = JSON.parse(r);
  if (!btn.error) {
    await sleep(300);
    await clickAt(send, btn.x, btn.y);
    return true;
  }
  return false;
}

async function getPageState(eval_) {
  const r = await eval_(`
    const url = location.href;
    const step = url.split('/').pop().split('?')[0];
    const body = document.body.innerText.substring(0, 600);
    const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        id: el.id, type: el.type, tag: el.tagName,
        placeholder: el.placeholder?.substring(0, 40) || '',
        label: el.labels?.[0]?.textContent?.trim()?.substring(0, 50) || el.getAttribute('aria-label')?.substring(0, 50) || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    const allBtns = Array.from(document.querySelectorAll('button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 40));
    return JSON.stringify({ url, step, body, inputs, allBtns });
  `);
  return JSON.parse(r);
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Step 1: Click "Fill out manually"
  console.log("=== Resume Import ===");
  await findAndClickButton(send, eval_, "Fill out manually");
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  // Process each step
  for (let i = 0; i < 15; i++) {
    const state = await getPageState(eval_);
    console.log(`\n=== ${state.step} (${i+2}/10) ===`);
    console.log(`Inputs: ${state.inputs.length}, Buttons: ${state.allBtns.join(' | ')}`);
    console.log(`Body: ${state.body.substring(0, 200)}`);

    // Check if done
    if (state.url.includes('dashboard') || state.url.includes('best-matches') || state.url.includes('feed') ||
        state.body.includes('profile is ready') || state.body.includes('Looking good')) {
      console.log("\n*** PROFILE COMPLETE ***");
      break;
    }

    // Handle each step type
    const step = state.step;

    if (step === 'categories' || state.body.includes('kind of work')) {
      // Search for a category
      if (state.inputs.length > 0) {
        await clickAt(send, state.inputs[0].x, state.inputs[0].y);
        await sleep(300);
        await send("Input.insertText", { text: "Data Entry" });
        await sleep(2000);
        // Click suggestion
        const r = await eval_(`
          const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li, ul li'))
            .filter(el => el.offsetParent !== null && el.textContent.includes('Data Entry'))
            .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
          return JSON.stringify(opts);
        `);
        const opts = JSON.parse(r);
        if (opts.length > 0) {
          await clickAt(send, opts[0].x, opts[0].y);
          console.log(`Selected: ${opts[0].text}`);
        }
        await sleep(500);
      }
    } else if (step === 'skills' || state.body.includes('skills')) {
      // Add some skills
      if (state.inputs.length > 0) {
        const skills = ["Data Entry", "Microsoft Excel", "Proofreading", "Resume Writing"];
        for (const skill of skills) {
          await clickAt(send, state.inputs[0].x, state.inputs[0].y);
          await sleep(200);
          await send("Input.insertText", { text: skill });
          await sleep(1500);
          const r = await eval_(`
            const opts = Array.from(document.querySelectorAll('[role="option"], [class*="suggestion"] li, ul li'))
              .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 0)
              .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
            return JSON.stringify(opts.slice(0, 3));
          `);
          const opts = JSON.parse(r);
          if (opts.length > 0) {
            await clickAt(send, opts[0].x, opts[0].y);
            console.log(`Skill: ${opts[0].text}`);
          }
          await sleep(500);
          // Clear search
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
          await sleep(300);
        }
      }
    } else if (step === 'title' || state.body.includes('professional title')) {
      if (state.inputs.length > 0) {
        await clickAt(send, state.inputs[0].x, state.inputs[0].y);
        await sleep(200);
        await send("Input.insertText", { text: "BIM Specialist | Technical Writer | Data Entry Expert" });
        console.log("Title set");
      }
    } else if (step === 'overview' || step === 'bio' || state.body.includes('professional bio') || state.body.includes('overview')) {
      const textarea = state.inputs.find(i => i.tag === 'TEXTAREA');
      if (textarea) {
        await clickAt(send, textarea.x, textarea.y);
        await sleep(200);
        await send("Input.insertText", { text: "Experienced BIM specialist and technical professional with expertise in Revit, AutoCAD, and building information modeling. I offer high-quality writing, data entry, and document management services. Detail-oriented with a strong commitment to accuracy and timely delivery. Skilled in creating professional resumes, technical documents, and business content." });
        console.log("Bio set");
      }
    } else if (step === 'rate' || state.body.includes('hourly rate') || state.body.includes('per hour')) {
      if (state.inputs.length > 0) {
        await clickAt(send, state.inputs[0].x, state.inputs[0].y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.insertText", { text: "25.00" });
        console.log("Rate: $25/hr");
      }
    } else if (step === 'photo' || state.body.includes('profile photo')) {
      // Skip photo for now
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
    } else if (step === 'experience' || step === 'employment' || state.body.includes('work experience')) {
      // Skip for now
    } else if (step === 'education' || state.body.includes('education')) {
      // Skip for now
    }

    // Try to advance: Next > Skip > specific buttons
    await sleep(500);
    let advanced = await findAndClickButton(send, eval_, "Next");
    if (!advanced) advanced = await findAndClickButton(send, eval_, "Review");
    if (!advanced) advanced = await findAndClickButton(send, eval_, "Submit");
    if (!advanced) advanced = await findAndClickButton(send, eval_, "Skip");
    if (!advanced) advanced = await findAndClickButton(send, eval_, "Save");
    if (!advanced) advanced = await findAndClickButton(send, eval_, "Continue");

    if (!advanced) {
      console.log("No navigation button found, trying to go to next URL manually");
      break;
    }

    await sleep(3000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
