// Fill gig #3 description (wizard=2) and save
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  // Verify wizard=2
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard')
    });
  `);
  console.log("State:", r);

  // === DESCRIPTION ===
  console.log("=== Description ===");

  // Click into the Quill editor
  r = await eval_(`
    const editor = document.querySelector('.ql-editor');
    if (editor) {
      editor.scrollIntoView({ block: 'center' });
      editor.focus();
      const rect = editor.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + 20), y: Math.round(rect.y + 20) });
    }
    return JSON.stringify({ error: 'no editor' });
  `);
  console.log("Editor:", r);
  const editorPos = JSON.parse(r);

  if (!editorPos.error) {
    await clickAt(send, editorPos.x, editorPos.y);
    await sleep(300);

    // Select all and delete
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
    await sleep(100);
    await send("Input.dispatchKeyEvent", { type: "keyDown", key: "Backspace", code: "Backspace" });
    await send("Input.dispatchKeyEvent", { type: "keyUp", key: "Backspace", code: "Backspace" });
    await sleep(200);

    // Type the description
    const description = `Are you struggling to land interviews? A well-crafted resume and cover letter can make all the difference. I will create a professional, ATS-friendly resume and compelling cover letter that highlights your unique skills and experience.

What you'll get:

- Professionally written resume tailored to your target industry
- ATS-optimized formatting to pass automated screening systems
- Strategic keyword placement for maximum visibility
- Clean, modern design that stands out to hiring managers
- Cover letter customized for your specific job target
- Quick turnaround with unlimited revisions

My process:
1. Review your current resume and career goals
2. Research your target industry and role requirements
3. Write compelling content that showcases your achievements
4. Format everything in a clean, professional layout
5. Deliver editable files (Word/PDF) ready to submit

Whether you're a recent graduate, career changer, or experienced professional, I'll help you present your best self on paper. Order now and take the first step toward your dream job!`;

    await send("Input.insertText", { text: description });
    await sleep(500);

    // Check character count
    r = await eval_(`
      const countText = document.body.innerText.match(/(\\d+)\\/1200/);
      return countText ? countText[0] : 'count not found';
    `);
    console.log("Character count:", r);
  }

  // === SAVE ===
  console.log("\n=== Save ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(1000);

  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'no button' });
  `);
  const saveBtn = JSON.parse(r);

  if (!saveBtn.error) {
    console.log(`Clicking Save at (${saveBtn.x}, ${saveBtn.y})`);
    await clickAt(send, saveBtn.x, saveBtn.y);
    await sleep(8000);

    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="invalid"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors
      });
    `);
    console.log("After save:", r);

    // If still wizard=2, try navigating to wizard=3
    const state = JSON.parse(r);
    if (state.wizard === '2' && state.errors.length === 0) {
      console.log("Navigating to wizard=3...");
      const newUrl = state.url.replace('wizard=2', 'wizard=3');
      await eval_(`window.location.href = '${newUrl}'`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard'),
          body: document.body?.innerText?.substring(0, 300)
        });
      `);
      console.log("Wizard=3:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
