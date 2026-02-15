// Upwork profile - continue from languages (7/10) through completion
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  let lastStep = '';
  let stuckCount = 0;

  for (let iteration = 0; iteration < 15; iteration++) {
    let r = await eval_(`
      const url = location.href;
      const step = url.split('/').pop().split('?')[0];
      const body = document.body.innerText.substring(0, 1000);
      const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="checkbox"]):not([type="radio"]), textarea'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          id: el.id, type: el.type, tag: el.tagName,
          placeholder: (el.placeholder || '').substring(0, 50),
          value: el.value.substring(0, 50),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      const btns = Array.from(document.querySelectorAll('button, a'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50
          && !el.textContent.trim().includes('Skip to content'))
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          tag: el.tagName,
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify({ url, step, body, inputs, btns });
    `);
    const state = JSON.parse(r);
    console.log(`\n=== Step: ${state.step} (iter ${iteration}) ===`);
    console.log(`Body: ${state.body.substring(0, 250)}`);
    console.log(`Buttons: ${state.btns.map(b => b.text).join(' | ')}`);
    console.log(`Inputs: ${JSON.stringify(state.inputs)}`);

    // Check if done - only match on URL patterns, not body text
    if (state.url.includes('dashboard') || state.url.includes('best-matches') || state.url.includes('feed') ||
        state.url.includes('complete') || state.body.includes('profile is ready') ||
        state.body.includes('start searching for jobs') || state.body.includes('Your profile has been')) {
      console.log("\n*** PROFILE COMPLETE ***");
      break;
    }

    // Detect stuck
    if (state.step === lastStep) {
      stuckCount++;
      if (stuckCount >= 2) {
        console.log("STUCK - trying skip");
        const skipBtn = state.btns.find(b => b.text.includes('Skip') && !b.text.includes('Skip to'));
        if (skipBtn) {
          await clickAt(send, skipBtn.x, skipBtn.y);
          await sleep(4000);
          ws.close(); await sleep(500);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          stuckCount = 0; lastStep = '';
          continue;
        }
      }
    } else {
      stuckCount = 0;
    }
    lastStep = state.step;

    const step = state.step;

    // Handle each step
    if (step === 'languages') {
      console.log("Languages - English pre-set, advancing");
    } else if (step === 'overview' || step === 'bio' || state.body.includes('write an overview') || state.body.includes('professional overview')) {
      const textarea = state.inputs.find(i => i.tag === 'TEXTAREA');
      if (textarea) {
        await clickAt(send, textarea.x, textarea.y);
        await sleep(200);
        // Select all and delete first
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
        await clickAt(send, state.inputs[0].x, state.inputs[0].y);
        await sleep(200);
        await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
        await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
        await sleep(50);
        await send("Input.insertText", { text: "25" });
        console.log("Rate: $25/hr");
        await sleep(500);
      }
    } else if (step === 'photo' || state.body.includes('profile photo')) {
      console.log("Photo step - will skip or continue");
    } else if (step === 'location' || state.body.includes('where are you')) {
      console.log("Location step");
    } else if (step === 'review' || state.body.includes('review your profile') || state.body.includes('almost done')) {
      console.log("Review step - submitting");
    }

    // Navigate forward
    await sleep(500);
    let advanced = false;

    // Primary: Next button
    const nextBtn = state.btns.find(b =>
      (b.text.includes('Next') || b.text === 'Review your profile' || b.text.includes('Submit') ||
       b.text === 'Continue' || b.text.includes('Review profile'))
      && b.tag === 'BUTTON'
    );
    if (nextBtn) {
      await clickAt(send, nextBtn.x, nextBtn.y);
      console.log(`Clicked: ${nextBtn.text}`);
      advanced = true;
    }

    // Fallback: any button-like link with Next
    if (!advanced) {
      const nextLink = state.btns.find(b =>
        (b.text.includes('Next') || b.text.includes('Submit') || b.text.includes('Review'))
      );
      if (nextLink) {
        await clickAt(send, nextLink.x, nextLink.y);
        console.log(`Clicked link: ${nextLink.text}`);
        advanced = true;
      }
    }

    // Last resort: Skip
    if (!advanced) {
      const skipBtn = state.btns.find(b => b.text.includes('Skip') && !b.text.includes('Skip to'));
      if (skipBtn) {
        await clickAt(send, skipBtn.x, skipBtn.y);
        console.log(`Clicked: ${skipBtn.text}`);
        advanced = true;
      }
    }

    if (!advanced) {
      console.log("No button found");
      break;
    }

    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
