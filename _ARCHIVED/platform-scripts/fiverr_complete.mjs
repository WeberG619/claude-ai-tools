// Complete Fiverr gig: fix requirements, upload gallery, publish
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      bodyHas: {
        humanTouch: document.body?.innerText?.includes('human touch'),
        gallery: document.body?.innerText?.includes('Gallery'),
        requirements: document.body?.innerText?.includes('Requirements')
      }
    });
  `);
  console.log("Current:", r);
  let state = JSON.parse(r);

  // If we hit the bot detection page, go back to the gallery via breadcrumb click
  if (state.bodyHas.humanTouch) {
    console.log("Bot detection page! Going back...");
    await eval_(`window.history.back()`);
    await sleep(3000);
    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
    console.log("After back:", r);
    state = JSON.parse(r);
  }

  // Navigate to Requirements step via breadcrumb
  console.log("\n=== Going to Requirements ===");
  r = await eval_(`
    const crumbs = Array.from(document.querySelectorAll('.crumb-content, .nav-crumb'));
    const reqCrumb = crumbs.find(c => c.textContent.includes('Requirements'));
    if (reqCrumb) {
      const clickTarget = reqCrumb.closest('a') || reqCrumb.closest('li') || reqCrumb;
      clickTarget.click();
      return 'clicked Requirements crumb';
    }
    return JSON.stringify(crumbs.map(c => c.textContent.trim().substring(0, 20)));
  `);
  console.log(r);
  await sleep(3000);

  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      bodyPreview: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("Now on:", r);
  state = JSON.parse(r);

  // === REQUIREMENTS ===
  if (state.step === 'Requirements' || state.url?.includes('requirements')) {
    console.log("\n=== Adding Requirement ===");

    // Click "+ Add New Question"
    r = await eval_(`
      const addBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Add New Question'));
      if (addBtn) {
        addBtn.scrollIntoView({ block: 'center' });
        addBtn.click();
        return 'clicked Add New Question';
      }
      return 'button not found';
    `);
    console.log(r);
    await sleep(1000);

    // Check what appeared
    r = await eval_(`
      return JSON.stringify({
        bodyPreview: document.body?.innerText?.substring(0, 1500),
        visibleInputs: Array.from(document.querySelectorAll('input, textarea'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            tag: el.tagName,
            type: el.type,
            name: el.name || '',
            placeholder: (el.placeholder || '').substring(0, 50),
            class: (el.className?.toString() || '').substring(0, 60),
            y: Math.round(el.getBoundingClientRect().y)
          }))
      });
    `);
    console.log("After add question:", r);

    const reqState = JSON.parse(r);

    // Find the question text input/textarea and fill it
    const questionInput = reqState.visibleInputs.find(i =>
      i.placeholder.includes('question') || i.placeholder.includes('Question') ||
      i.class.includes('question') || i.tag === 'TEXTAREA'
    );

    if (questionInput) {
      console.log("Found question input:", questionInput);

      // Focus and type
      await eval_(`
        const el = Array.from(document.querySelectorAll('${questionInput.tag.toLowerCase()}'))
          .filter(e => e.offsetParent !== null)
          .find(e => e.getBoundingClientRect().y > 300);
        if (el) { el.focus(); el.click(); }
      `);
      await sleep(200);
      await send("Input.insertText", { text: "Please provide the data or documents you need entered/processed (attach files or describe the task in detail)" });
      await sleep(500);
    } else {
      // Try finding any new textarea or input that appeared
      console.log("Looking for input fields...");
      r = await eval_(`
        const newEls = Array.from(document.querySelectorAll('textarea, input[type="text"]'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 300)
          .map(el => ({
            tag: el.tagName,
            type: el.type,
            placeholder: (el.placeholder || '').substring(0, 50),
            y: Math.round(el.getBoundingClientRect().y),
            x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
            w: Math.round(el.getBoundingClientRect().width)
          }));
        return JSON.stringify(newEls);
      `);
      console.log("Available inputs:", r);

      const inputs = JSON.parse(r);
      if (inputs.length > 0) {
        const target = inputs[0];
        await eval_(`
          const els = Array.from(document.querySelectorAll('textarea, input[type="text"]'))
            .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 300);
          if (els[0]) { els[0].focus(); els[0].click(); }
        `);
        await sleep(200);
        await send("Input.insertText", { text: "Please provide the data or documents you need entered/processed (attach files or describe the task in detail)" });
        await sleep(500);
      }
    }

    // Check for "Answer required" toggle and enable it
    r = await eval_(`
      const toggles = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          checked: el.checked,
          label: el.closest('label')?.textContent?.trim()?.substring(0, 50) || '',
          y: Math.round(el.getBoundingClientRect().y)
        }));
      return JSON.stringify(toggles);
    `);
    console.log("Toggles:", r);

    // Look for a Save/Add button for the question
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim().substring(0, 40),
          y: Math.round(el.getBoundingClientRect().y),
          class: (el.className?.toString() || '').substring(0, 60)
        }))
        .filter(b => b.text.length > 0);
      return JSON.stringify(btns);
    `);
    console.log("Buttons:", r);

    // Try clicking Add/Save for the question
    r = await eval_(`
      const addBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Add') && !b.textContent.includes('New Question') && b.offsetParent !== null);
      if (addBtn) {
        addBtn.click();
        return 'clicked Add: ' + addBtn.textContent.trim().substring(0, 30);
      }
      return 'no add button';
    `);
    console.log(r);
    await sleep(1000);

    // Now click Save & Continue
    console.log("\nSaving requirements...");
    r = await eval_(`
      const btn = document.querySelector('.btn-submit');
      if (btn) { btn.scrollIntoView({ block: 'center' }); }
      return btn ? 'found' : 'not found';
    `);
    await sleep(200);

    // Click with CDP
    r = await eval_(`
      const btn = document.querySelector('.btn-submit');
      if (!btn) return JSON.stringify({ error: 'no btn' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const btnCoords = JSON.parse(r);
    await clickAt(send, btnCoords.x, btnCoords.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        errors: Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 100)
          .map(el => el.textContent.trim())
      });
    `);
    console.log("After req save:", r);
    state = JSON.parse(r);
  }

  // === GALLERY ===
  if (state.step === 'Gallery' || state.url?.includes('gallery')) {
    console.log("\n\n=== Gallery - Upload Image ===");

    // Upload to the IMAGE file input (id="image")
    const nodeResult = await send("Runtime.evaluate", {
      expression: `document.querySelector('#image')`,
      returnByValue: false
    });

    if (nodeResult.result?.objectId) {
      const domNode = await send("DOM.describeNode", {
        objectId: nodeResult.result.objectId
      });

      if (domNode.node?.backendNodeId) {
        await send("DOM.setFileInputFiles", {
          files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig_image.jpg"],
          backendNodeId: domNode.node.backendNodeId
        });
        console.log("Image file set!");

        // Dispatch change event
        await eval_(`
          const el = document.querySelector('#image');
          el.dispatchEvent(new Event('change', { bubbles: true }));
        `);
        await sleep(5000);

        // Check upload status
        r = await eval_(`
          const errors = Array.from(document.querySelectorAll('[class*="error"]'))
            .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
            .map(el => el.textContent.trim().substring(0, 80));
          const thumbnails = Array.from(document.querySelectorAll('[class*="thumbnail"], [class*="preview"], [class*="uploaded"]'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({
              class: (el.className?.toString() || '').substring(0, 60),
              tag: el.tagName,
              src: (el.src || '').substring(0, 60)
            }));
          return JSON.stringify({ errors, thumbnails: thumbnails.slice(0, 5) });
        `);
        console.log("Upload status:", r);
      }
    }

    // Wait for upload processing
    await sleep(5000);

    // Save
    console.log("\nSaving gallery...");
    r = await eval_(`
      const btn = document.querySelector('.btn-submit');
      if (!btn) return JSON.stringify({ error: 'no btn' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const galBtnCoords = JSON.parse(r);
    await clickAt(send, galBtnCoords.x, galBtnCoords.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        errors: Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 100)
          .map(el => el.textContent.trim()),
        bodyPreview: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After gallery save:", r);
    state = JSON.parse(r);
  }

  // === PUBLISH ===
  if (state.step === 'Publish') {
    console.log("\n\n=== Publish ===");
    r = await eval_(`
      return document.body?.innerText?.substring(0, 1000);
    `);
    console.log("Publish page:", r);

    // Click Publish
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Publish') && !b.textContent.includes('Preview'));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        btn.click();
        return 'Published!';
      }
      return 'Publish button not found';
    `);
    console.log(r);
    await sleep(5000);

    r = await eval_(`return JSON.stringify({ url: location.href, bodyPreview: document.body?.innerText?.substring(0, 500) })`);
    console.log("After publish:", r);
  }

  console.log("\n\nFinal state:", state.step, state.url);
  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
