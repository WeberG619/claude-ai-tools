// Check current step and complete remaining steps (Description, Requirements, Gallery, Publish)
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

async function clickSaveAndContinue(send, eval_) {
  let r = await eval_(`
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
  const btn = JSON.parse(r);
  if (!btn.error) {
    await clickAt(send, btn.x, btn.y);
    await sleep(5000);
    return true;
  }
  return false;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Check which step we're on
  let r = await eval_(`
    // Check for active step indicator
    const activeStep = document.querySelector('[class*="active-step"], .step-active, [class*="wizard-step"][class*="active"]');
    const wizardParam = new URL(location.href).searchParams.get('wizard');

    // Get the main content heading/section
    const mainContent = document.querySelector('[class*="editor-content"], [class*="wizard-content"], main');

    return JSON.stringify({
      url: location.href,
      wizard: wizardParam,
      activeStepText: activeStep?.textContent?.trim()?.substring(0, 30) || '',
      body: (document.body?.innerText || '').substring(200, 1500)
    });
  `);
  console.log("Current state:", r);
  const state = JSON.parse(r);

  // Determine current step from URL wizard param or content
  const wizardStep = parseInt(state.wizard) || 0;
  console.log(`Wizard step: ${wizardStep}`);

  // Step 2 = Description & FAQ (wizard=2)
  if (state.body.includes('Describe Your Gig') || state.body.includes('Description') && state.body.includes('briefly describe') || wizardStep === 2) {
    console.log("\n=== Step 3: Description & FAQ ===");

    // Find the description textarea/editor
    r = await eval_(`
      const editors = Array.from(document.querySelectorAll('textarea, [contenteditable="true"], [class*="editor"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 50)
        .map(el => ({
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 60),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + 20),
          h: Math.round(el.getBoundingClientRect().height),
          contentEditable: el.contentEditable
        }));
      return JSON.stringify(editors);
    `);
    console.log("Editors:", r);
    const editors = JSON.parse(r);

    if (editors.length > 0) {
      const editor = editors[0];
      const description = `Are you looking for a skilled proofreader and editor to polish your writing? I offer professional proofreading, editing, and rewriting services to ensure your content is clear, error-free, and impactful.

What you'll get:
- Thorough grammar, spelling, and punctuation correction
- Improved sentence structure and clarity
- Consistent tone and style throughout
- Enhanced readability and flow
- Track changes so you can see all edits made

I work with:
- Articles and blog posts
- Website content
- Academic papers and theses
- Books and manuscripts
- Business documents and reports
- Resumes and cover letters

Every piece of content deserves careful attention. I'll make sure your writing communicates exactly what you intend, with professional polish.

Order now and let me help your words make the right impression!`;

      console.log("Clicking editor...");
      await clickAt(send, editor.x, editor.y);
      await sleep(500);
      await send("Input.dispatchKeyEvent", { type: "keyDown", key: "a", code: "KeyA", modifiers: 2 });
      await send("Input.dispatchKeyEvent", { type: "keyUp", key: "a", code: "KeyA", modifiers: 2 });
      await sleep(100);
      await send("Input.insertText", { text: description });
      await sleep(500);
      console.log("Description filled");
    }

    // Save & Continue to next step
    if (await clickSaveAndContinue(send, eval_)) {
      r = await eval_(`return location.href`);
      console.log("After save:", r);
    }
  }

  // Check if we're on Requirements step (wizard=3)
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 1000)
    });
  `);
  const step3 = JSON.parse(r);
  console.log(`\nCurrent wizard: ${step3.wizard}`);

  if (step3.body.includes('Requirement') || step3.wizard === '3') {
    console.log("\n=== Step 4: Requirements ===");
    // Requirements step - usually has text area for buyer requirements
    r = await eval_(`
      const textareas = Array.from(document.querySelectorAll('textarea'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().height > 30)
        .map(el => ({
          placeholder: el.placeholder?.substring(0, 60) || '',
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          y: Math.round(el.getBoundingClientRect().y + 10)
        }));
      return JSON.stringify(textareas);
    `);
    console.log("Requirement textareas:", r);

    // Can often skip requirements or just save
    if (await clickSaveAndContinue(send, eval_)) {
      console.log("Requirements saved");
    }
  }

  // Check if on Gallery step (wizard=4)
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 1000)
    });
  `);
  const step4 = JSON.parse(r);
  console.log(`\nCurrent wizard: ${step4.wizard}`);

  if (step4.body.includes('Gallery') || step4.body.includes('image') || step4.wizard === '4') {
    console.log("\n=== Step 5: Gallery ===");
    // Gallery often requires at least one image, but we can try to save without
    if (await clickSaveAndContinue(send, eval_)) {
      console.log("Gallery saved");
    }
  }

  // Check if on Publish step (wizard=5)
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(0, 2000)
    });
  `);
  const step5 = JSON.parse(r);
  console.log(`\nCurrent wizard: ${step5.wizard}`);
  console.log("Body:", step5.body.substring(0, 800));

  if (step5.body.includes('Publish') || step5.wizard === '5') {
    console.log("\n=== Step 6: Publish ===");
    r = await eval_(`
      const publishBtn = Array.from(document.querySelectorAll('button, a'))
        .find(el => el.textContent.trim().includes('Publish') && el.offsetParent !== null);
      if (publishBtn) {
        const rect = publishBtn.getBoundingClientRect();
        return JSON.stringify({
          text: publishBtn.textContent.trim().substring(0, 30),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
      return JSON.stringify({ error: 'no publish button' });
    `);
    console.log("Publish button:", r);
    const pubBtn = JSON.parse(r);
    if (!pubBtn.error) {
      await clickAt(send, pubBtn.x, pubBtn.y);
      await sleep(5000);
      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          body: (document.body?.innerText || '').substring(0, 500)
        });
      `);
      console.log("After publish:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
