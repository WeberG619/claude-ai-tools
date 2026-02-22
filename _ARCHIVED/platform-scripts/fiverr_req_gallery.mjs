// Fix Fiverr requirements then gallery upload via file chooser interception
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

  // Check current page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim()
    });
  `);
  console.log("Current:", r);
  let state = JSON.parse(r);

  // === STEP 1: Navigate to Requirements ===
  if (state.step !== 'Requirements') {
    console.log("\n=== Navigating to Requirements ===");
    // Click the "Requirements" link in breadcrumb - find the clickable element
    r = await eval_(`
      // Find the nav crumbs
      const navItems = Array.from(document.querySelectorAll('li'));
      const reqItem = navItems.find(li => li.textContent.includes('Requirements'));
      if (reqItem) {
        // Find the span with the text
        const span = reqItem.querySelector('.crumb-content') || reqItem.querySelector('span');
        if (span) {
          span.click();
          return 'clicked span in li';
        }
        reqItem.click();
        return 'clicked li';
      }
      return 'not found';
    `);
    console.log("Nav click:", r);
    await sleep(3000);

    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
    console.log("After nav:", r);
    state = JSON.parse(r);

    // If didn't work, try using the Back button
    if (state.step !== 'Requirements') {
      console.log("Breadcrumb didn't work. Using Back button...");
      r = await eval_(`
        const backBtn = Array.from(document.querySelectorAll('button, a'))
          .find(el => el.textContent.trim() === 'Back');
        if (backBtn) { backBtn.click(); return 'clicked Back'; }
        return 'no Back button';
      `);
      console.log(r);
      await sleep(3000);

      r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
      console.log("After back:", r);
      state = JSON.parse(r);
    }
  }

  // === STEP 2: Add Requirement ===
  if (state.step === 'Requirements') {
    console.log("\n=== Adding Requirement ===");

    // Click "+ Add New Question"
    r = await eval_(`
      const addBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Add New Question'));
      if (!addBtn) return JSON.stringify({ error: 'no add button' });
      addBtn.scrollIntoView({ block: 'center' });
      const rect = addBtn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    console.log("Add button:", r);
    const addCoords = JSON.parse(r);
    if (!addCoords.error) {
      await clickAt(send, addCoords.x, addCoords.y);
      await sleep(1500);

      // Check what appeared
      r = await eval_(`
        return JSON.stringify({
          bodyPreview: document.body?.innerText?.substring(0, 2000),
          newInputs: Array.from(document.querySelectorAll('textarea, input[type="text"]'))
            .filter(el => el.offsetParent !== null)
            .map(el => ({
              tag: el.tagName,
              placeholder: (el.placeholder || '').substring(0, 50),
              class: (el.className?.toString() || '').substring(0, 60),
              y: Math.round(el.getBoundingClientRect().y),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
              w: Math.round(el.getBoundingClientRect().width)
            }))
        });
      `);
      console.log("After add click:", r);

      const formState = JSON.parse(r);

      // Type in the question field
      if (formState.newInputs.length > 0) {
        // Find the question text input (probably the first or the one with a question-related placeholder)
        const qInput = formState.newInputs.find(i => i.placeholder.includes('question') || i.placeholder.includes('Type') || i.w > 200) || formState.newInputs[0];
        console.log("Typing in:", qInput);

        await eval_(`
          const inputs = Array.from(document.querySelectorAll('textarea, input[type="text"]'))
            .filter(el => el.offsetParent !== null);
          const target = inputs.find(i => i.getBoundingClientRect().y > 400) || inputs[inputs.length - 1];
          if (target) { target.focus(); target.click(); }
        `);
        await sleep(300);
        await send("Input.insertText", { text: "Please provide the data or documents you need entered/processed. Attach files or describe your requirements." });
        await sleep(500);

        // Look for an "Add" or "Save" button for this question
        r = await eval_(`
          const btns = Array.from(document.querySelectorAll('button'))
            .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 400)
            .map(el => ({
              text: el.textContent.trim().substring(0, 40),
              y: Math.round(el.getBoundingClientRect().y),
              x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2)
            }))
            .filter(b => b.text.length > 0);
          return JSON.stringify(btns);
        `);
        console.log("Question buttons:", r);

        const qBtns = JSON.parse(r);
        // Click Add/Save button for the question
        const addQBtn = qBtns.find(b => b.text.includes('Add') || b.text.includes('Save'));
        if (addQBtn) {
          console.log(`Clicking "${addQBtn.text}"`);
          await clickAt(send, addQBtn.x, addQBtn.y);
          await sleep(1000);
        }
      }

      // Check if requirement was added
      r = await eval_(`
        return JSON.stringify({
          bodyText: document.body?.innerText?.substring(0, 1000),
          hasQuestion: document.body?.innerText?.includes('Please provide the data')
        });
      `);
      console.log("Requirement added?", JSON.parse(r).hasQuestion);
    }

    // Save & Continue
    console.log("\nSaving requirements...");
    await sleep(500);
    r = await eval_(`
      const btn = document.querySelector('.btn-submit');
      if (!btn) return JSON.stringify({ error: 'no btn' });
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const saveCoords = JSON.parse(r);
    if (!saveCoords.error) {
      await clickAt(send, saveCoords.x, saveCoords.y);
      await sleep(5000);
    }

    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
    console.log("After save:", r);
    state = JSON.parse(r);
  }

  // === STEP 3: Gallery Upload ===
  if (state.step === 'Gallery') {
    console.log("\n\n=== Gallery - Upload via File Chooser ===");

    // Enable file chooser interception
    await send("Page.setInterceptFileChooserDialog", { enabled: true });

    // Set up handler for file chooser events
    let fileChooserResolved = false;
    const handleFileChooser = async () => {
      // Listen for the file chooser event
      return new Promise((resolve) => {
        const handler = async (event) => {
          const msg = JSON.parse(event.data);
          if (msg.method === 'Page.fileChooserOpened') {
            console.log("File chooser opened!");
            // Handle it by providing the file
            await send("Page.handleFileChooser", {
              action: "accept",
              files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig_image.jpg"]
            });
            console.log("File provided!");
            fileChooserResolved = true;
            ws.removeEventListener("message", handler);
            resolve(true);
          }
        };
        ws.addEventListener("message", handler);

        // Timeout after 10 seconds
        setTimeout(() => {
          ws.removeEventListener("message", handler);
          resolve(false);
        }, 10000);
      });
    };

    // Start listening for file chooser, then click Browse button for images
    const chooserPromise = handleFileChooser();

    // Find and click the Images "Browse" button
    r = await eval_(`
      // Find the "Images" section and its Browse button
      const sections = Array.from(document.querySelectorAll('*'))
        .filter(el => el.textContent?.includes('Images (up to 3)') && el.children.length < 5);

      // Find Browse buttons
      const browseLinks = Array.from(document.querySelectorAll('a, button, span'))
        .filter(el => el.textContent.trim() === 'Browse' && el.offsetParent !== null)
        .map(el => ({
          text: el.textContent.trim(),
          tag: el.tagName,
          class: (el.className?.toString() || '').substring(0, 60),
          y: Math.round(el.getBoundingClientRect().y),
          x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
          parentText: el.parentElement?.textContent?.trim()?.substring(0, 60) || ''
        }));

      return JSON.stringify({ sections: sections.map(s => s.textContent.trim().substring(0, 50)), browseLinks });
    `);
    console.log("Browse buttons:", r);
    const browseInfo = JSON.parse(r);

    // Find the Browse button in the Images section (not Video or PDF)
    // The order should be: Video Browse, Images Browse, PDF Browse
    const imageBrowse = browseInfo.browseLinks.find(b => b.parentText.includes('Photo')) ||
                        browseInfo.browseLinks[1]; // Second browse is usually for images

    if (imageBrowse) {
      console.log(`Clicking Images Browse at (${imageBrowse.x}, ${imageBrowse.y})`);
      await clickAt(send, imageBrowse.x, imageBrowse.y);
    }

    // Wait for file chooser
    const result = await chooserPromise;
    console.log("File chooser handled:", result);

    // Wait for upload to process
    await sleep(8000);

    // Check status
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 80));
      const thumbs = Array.from(document.querySelectorAll('[class*="thumbnail"], [class*="preview-img"], [class*="upload-image"]'))
        .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 30)
        .map(el => ({
          class: (el.className?.toString() || '').substring(0, 60),
          w: Math.round(el.getBoundingClientRect().width)
        }));
      return JSON.stringify({ errors, thumbnails: thumbs.slice(0, 5), bodySnippet: document.body?.innerText?.substring(0, 500) });
    `);
    console.log("Upload status:", r);

    // Disable file chooser interception
    await send("Page.setInterceptFileChooserDialog", { enabled: false });

    // Try saving
    console.log("\nSaving gallery...");
    r = await eval_(`
      const btn = document.querySelector('.btn-submit');
      if (!btn) return JSON.stringify({ error: 'no btn' });
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    `);
    const galCoords = JSON.parse(r);
    if (!galCoords.error) {
      await clickAt(send, galCoords.x, galCoords.y);
      await sleep(5000);
    }

    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim(), errors: Array.from(document.querySelectorAll('[class*="error"]')).filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 100).map(el => el.textContent.trim()) })`);
    console.log("After gallery save:", r);
    state = JSON.parse(r);
  }

  // === PUBLISH ===
  if (state.step === 'Publish') {
    console.log("\n\n=== Publishing Gig ===");
    r = await eval_(`return document.body?.innerText?.substring(0, 800)`);
    console.log("Publish page:", r);

    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().toLowerCase().includes('publish') && !b.textContent.includes('Preview'));
      if (btn) {
        btn.scrollIntoView({ block: 'center' });
        btn.click();
        return 'Published!';
      }
      return 'no publish btn';
    `);
    console.log(r);
    await sleep(5000);

    r = await eval_(`return JSON.stringify({ url: location.href, bodyPreview: document.body?.innerText?.substring(0, 500) })`);
    console.log("After publish:", r);
  }

  console.log("\n\nDone. Step:", state.step, "URL:", state.url);
  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
