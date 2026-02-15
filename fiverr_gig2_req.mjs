// Add a requirement question and save
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Scroll down to see the "Add new question" section
  await eval_(`window.scrollTo(0, 400)`);
  await sleep(500);

  // Look for "Add new question" or "+ Add" button in YOUR QUESTIONS section
  let r = await eval_(`
    const buttons = Array.from(document.querySelectorAll('button, a, [class*="add"]'))
      .filter(el => {
        const text = el.textContent.trim();
        return el.offsetParent !== null && (
          text.includes('Add new') || text.includes('+ Add') ||
          text.includes('Add Question') || text.includes('Add Requirement')
        );
      })
      .map(el => ({
        text: el.textContent.trim().substring(0, 40),
        tag: el.tagName,
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(buttons);
  `);
  console.log("Add buttons:", r);
  const addBtns = JSON.parse(r);

  // Click the first "Add" button
  if (addBtns.length > 0) {
    const btn = addBtns[0];
    console.log(`Clicking "${btn.text}" at (${btn.x}, ${btn.y})`);
    await clickAt(send, btn.x, btn.y);
    await sleep(1000);

    // Check what appeared
    r = await eval_(`
      const inputs = Array.from(document.querySelectorAll('textarea, input[type="text"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 0)
        .map(el => ({
          tag: el.tagName,
          placeholder: (el.placeholder || '').substring(0, 60),
          class: (el.className?.toString() || '').substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + 10)
        }));

      // Also check for select/dropdown for answer type
      const selects = Array.from(document.querySelectorAll('select, [class*="select"], [class*="dropdown"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 200)
        .map(el => ({
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 60),
          text: el.textContent.trim().substring(0, 60),
          y: Math.round(el.getBoundingClientRect().y)
        }));

      return JSON.stringify({ inputs, selects });
    `);
    console.log("Form elements:", r);
    const formEls = JSON.parse(r);

    // Find the question textarea/input and type a requirement
    if (formEls.inputs.length > 0) {
      const questionInput = formEls.inputs[0];
      console.log(`\nClicking question input at (${questionInput.x}, ${questionInput.y})`);
      await clickAt(send, questionInput.x, questionInput.y);
      await sleep(300);
      await send("Input.insertText", { text: "Please provide the document or text you need proofread/edited. Include any specific style guide preferences (APA, MLA, Chicago, etc.) or special instructions." });
      await sleep(500);
      console.log("Typed requirement question");

      // Look for an "Answer Type" selector and a "Required" checkbox
      r = await eval_(`
        const body = (document.body?.innerText || '').substring(0, 3000);
        const checkboxes = Array.from(document.querySelectorAll('input[type="checkbox"]'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.y > 200;
          })
          .map(el => ({
            checked: el.checked,
            label: (el.closest('label') || el.parentElement)?.textContent?.trim()?.substring(0, 40),
            x: Math.round(el.getBoundingClientRect().x + 10),
            y: Math.round(el.getBoundingClientRect().y + 10)
          }));

        // Look for Save/Add button
        const saveBtn = Array.from(document.querySelectorAll('button'))
          .filter(el => {
            const text = el.textContent.trim();
            return el.offsetParent !== null && (text === 'Add' || text === 'Save' || text === 'Done') && el.getBoundingClientRect().y > 200;
          })
          .map(el => ({
            text: el.textContent.trim(),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
          }));

        return JSON.stringify({ checkboxes, saveBtn });
      `);
      console.log("Checkboxes and save:", r);
      const { checkboxes, saveBtn } = JSON.parse(r);

      // Click "Add" or "Save" button for the question
      if (saveBtn.length > 0) {
        console.log(`Clicking "${saveBtn[0].text}" at (${saveBtn[0].x}, ${saveBtn[0].y})`);
        await clickAt(send, saveBtn[0].x, saveBtn[0].y);
        await sleep(1000);
      }
    }
  }

  // Now check if the requirement was added
  await sleep(500);
  r = await eval_(`
    const requirements = Array.from(document.querySelectorAll('[class*="requirement"], [class*="question"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('proofread'))
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(requirements);
  `);
  console.log("\nRequirements added:", r);

  // Try Save & Continue
  console.log("\n=== Saving ===");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  await sleep(800);

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
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100)),
        body: (document.body?.innerText || '').substring(200, 600)
      });
    `);
    console.log("\nAfter save:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
