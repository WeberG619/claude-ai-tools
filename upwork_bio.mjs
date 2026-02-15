// Upwork profile step 8-10: Bio, Rate/Photo, Review/Submit
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

  for (let iteration = 0; iteration < 12; iteration++) {
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
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 50
          && !el.textContent.trim().includes('Skip to content'))
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
        }));
      return JSON.stringify({ url, step, body, inputs, btns });
    `);
    const state = JSON.parse(r);
    console.log(`\n=== Step: ${state.step} (iter ${iteration}) ===`);
    console.log(`Body: ${state.body.substring(0, 200)}`);
    console.log(`Buttons: ${state.btns.map(b => b.text).join(' | ')}`);
    console.log(`Inputs: ${state.inputs.map(i => i.tag + ':' + i.type + ':' + i.placeholder).join(', ')}`);

    // Done check
    if (state.url.includes('/nx/find-work') || state.url.includes('dashboard') || state.url.includes('best-matches') ||
        state.url.includes('feed') || state.body.includes('start searching for jobs') ||
        state.body.includes('profile has been') || state.body.includes('Congratulations')) {
      console.log("\n*** PROFILE COMPLETE ***");
      break;
    }

    // Stuck detection
    if (state.step === lastStep) {
      stuckCount++;
      if (stuckCount >= 3) {
        console.log("STUCK - breaking");
        break;
      }
    } else {
      stuckCount = 0;
    }
    lastStep = state.step;

    const step = state.step;

    if (step === 'overview' || state.body.includes('write a bio')) {
      // Find textarea
      const textarea = state.inputs.find(i => i.tag === 'TEXTAREA');
      if (textarea) {
        // Scroll into view first
        await eval_(`
          const ta = document.querySelector('textarea');
          if (ta) ta.scrollIntoView({ block: 'center' });
        `);
        await sleep(300);
        // Re-get position
        r = await eval_(`
          const ta = document.querySelector('textarea');
          if (ta) {
            const rect = ta.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'none' });
        `);
        const taPos = JSON.parse(r);
        if (!taPos.error) {
          await clickAt(send, taPos.x, taPos.y);
          await sleep(200);
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
          await sleep(100);
          await send("Input.insertText", { text: "Experienced BIM specialist and technical professional with expertise in Revit, AutoCAD, and building information modeling. I offer high-quality writing, data entry, and document management services.\n\nKey strengths:\n- Technical writing and documentation\n- Professional resume and CV creation\n- Content writing and proofreading\n- Data entry with exceptional accuracy\n- BIM/CAD drafting and modeling\n\nDetail-oriented with a strong commitment to accuracy and timely delivery. Whether you need meticulous data entry, polished writing, or BIM/CAD drafting services, I deliver consistent, professional results." });
          console.log("Bio written");
          await sleep(500);
        }
      }
    } else if (step === 'rate' || state.body.includes('hourly rate') || state.body.includes('per hour') || state.body.includes('set your rate')) {
      if (state.inputs.length > 0) {
        // Scroll to input
        await eval_(`
          const inp = document.querySelector('input[type="number"], input[type="text"]');
          if (inp) inp.scrollIntoView({ block: 'center' });
        `);
        await sleep(300);
        r = await eval_(`
          const inp = document.querySelector('input[type="number"], input[type="text"]');
          if (inp && inp.offsetParent !== null) {
            const rect = inp.getBoundingClientRect();
            return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
          }
          return JSON.stringify({ error: 'none' });
        `);
        const inpPos = JSON.parse(r);
        if (!inpPos.error) {
          await clickAt(send, inpPos.x, inpPos.y);
          await sleep(200);
          await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
          await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
          await sleep(50);
          await send("Input.insertText", { text: "25" });
          console.log("Rate: $25/hr");
          await sleep(500);
        }
      }
    } else if (step === 'photo' || state.body.includes('profile photo')) {
      console.log("Photo - skipping");
    } else if (step === 'location' || state.body.includes('located')) {
      console.log("Location step");
    } else if (step === 'review' || state.body.includes('review your profile') || state.body.includes('almost done')) {
      console.log("Review - submitting profile");
    }

    // Navigate: scroll to button first, then click
    await sleep(500);
    let advanced = false;

    // Find and scroll to Next/Submit button
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => {
          const t = b.textContent.trim();
          return b.offsetParent !== null && !t.includes('Skip to content') &&
            (t.includes('Next') || t.includes('Review') || t.includes('Submit') || t.includes('Continue'));
        });
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        return 'scrolled to button';
      }
      return 'no button';
    `);
    await sleep(300);

    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => {
          const t = b.textContent.trim();
          return b.offsetParent !== null && !t.includes('Skip to content') &&
            (t.includes('Next') || t.includes('Review') || t.includes('Submit') || t.includes('Continue'));
        });
      if (btn) {
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'none' });
    `);
    const nextBtn = JSON.parse(r);
    if (!nextBtn.error) {
      await clickAt(send, nextBtn.x, nextBtn.y);
      console.log(`Clicked: ${nextBtn.text}`);
      advanced = true;
    }

    if (!advanced) {
      // Try skip
      r = await eval_(`
        const btn = Array.from(document.querySelectorAll('button'))
          .find(b => b.textContent.trim().includes('Skip') && !b.textContent.trim().includes('Skip to') && b.offsetParent !== null);
        if (btn) {
          btn.scrollIntoView({ block: 'center' });
          const rect = btn.getBoundingClientRect();
          return JSON.stringify({ text: btn.textContent.trim().substring(0, 40), x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
        }
        return JSON.stringify({ error: 'none' });
      `);
      const skipBtn = JSON.parse(r);
      if (!skipBtn.error) {
        await sleep(300);
        await clickAt(send, skipBtn.x, skipBtn.y);
        console.log(`Clicked: ${skipBtn.text}`);
        advanced = true;
      }
    }

    if (!advanced) {
      console.log("No navigation button");
      break;
    }

    await sleep(4000);
    ws.close(); await sleep(500);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
