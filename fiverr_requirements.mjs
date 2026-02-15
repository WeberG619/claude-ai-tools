// Fill Fiverr Requirements (Step 4), Gallery (Step 5), and Publish (Step 6)
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

async function main() {
  const { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check current step
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      bodyPreview: document.body?.innerText?.substring(0, 800)
    });
  `);
  console.log("Current:", r);
  let state = JSON.parse(r);

  // === STEP 4: Requirements ===
  if (state.step === 'Requirements') {
    console.log("\n=== Step 4: Requirements ===");

    // Requirements page usually has pre-populated questions from Fiverr
    // Just need to Save & Continue - requirements are optional
    r = await eval_(`
      // Check what's on the page
      const questions = Array.from(document.querySelectorAll('[class*="question"], [class*="requirement"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100));

      const toggles = Array.from(document.querySelectorAll('input[type="checkbox"]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          checked: el.checked,
          label: el.closest('label')?.textContent?.trim()?.substring(0, 50) || ''
        }));

      return JSON.stringify({ questions: questions.slice(0, 5), toggles });
    `);
    console.log("Requirements page:", r);

    // Save & Continue (requirements are optional)
    console.log("Saving requirements...");
    await eval_(`
      const btn = document.querySelector('.btn-submit') ||
        Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
      if (btn) btn.click();
    `);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        bodyPreview: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After requirements save:", r);
    state = JSON.parse(r);
  }

  // === STEP 5: Gallery ===
  if (state.step === 'Gallery') {
    console.log("\n=== Step 5: Gallery ===");

    // Gallery requires at least 1 image. Let me check what's needed.
    r = await eval_(`
      return JSON.stringify({
        bodyPreview: document.body?.innerText?.substring(0, 1000),
        fileInputs: Array.from(document.querySelectorAll('input[type="file"]')).map(f => ({
          name: f.name || '',
          accept: f.accept || '',
          class: (f.className?.toString() || '').substring(0, 60)
        })),
        buttons: Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null)
          .map(el => ({
            text: el.textContent.trim().substring(0, 40),
            y: Math.round(el.getBoundingClientRect().y)
          }))
          .filter(b => b.text.length > 0)
          .slice(0, 15)
      });
    `);
    console.log("Gallery page:", r);

    const galleryState = JSON.parse(r);

    // Gallery needs an image upload. Let's use the profile photo we already have
    if (galleryState.fileInputs.length > 0) {
      console.log("Uploading gallery image...");
      const photoPath = "D:\\\\CLAUDE-TOOLS\\\\weber_profile_photo.jpg";

      // Find the file input node
      r = await eval_(`
        const fileInput = document.querySelector('input[type="file"]');
        if (!fileInput) return JSON.stringify({ error: 'no file input' });
        return JSON.stringify({
          accept: fileInput.accept,
          multiple: fileInput.multiple
        });
      `);
      console.log("File input:", r);

      // Get the DOM node for file upload
      const nodeResult = await send("Runtime.evaluate", {
        expression: `document.querySelector('input[type="file"]')`,
        returnByValue: false
      });

      if (nodeResult.result?.objectId) {
        // Request the DOM node
        const domNode = await send("DOM.describeNode", {
          objectId: nodeResult.result.objectId
        });

        if (domNode.node?.backendNodeId) {
          // Set the file
          try {
            await send("DOM.setFileInputFiles", {
              files: ["D:\\_CLAUDE-TOOLS\\weber_profile_photo.jpg"],
              backendNodeId: domNode.node.backendNodeId
            });
            console.log("File set!");
            await sleep(2000);

            // Check if upload processed
            r = await eval_(`
              const imgs = Array.from(document.querySelectorAll('img'))
                .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 50)
                .map(el => ({
                  src: el.src?.substring(0, 60),
                  w: Math.round(el.getBoundingClientRect().width),
                  h: Math.round(el.getBoundingClientRect().height)
                }));
              const errors = Array.from(document.querySelectorAll('[class*="error"]'))
                .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
                .map(el => el.textContent.trim().substring(0, 80));
              return JSON.stringify({ imgs: imgs.slice(0, 5), errors });
            `);
            console.log("After upload:", r);
          } catch(e) {
            console.log("Upload error:", e.message);
          }
        }
      }
    }

    // Wait for upload to process
    await sleep(3000);

    // Try Save & Continue
    console.log("Saving gallery...");
    await eval_(`
      const btn = document.querySelector('.btn-submit') ||
        Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
      if (btn) btn.click();
    `);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 100)),
        bodyPreview: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After gallery save:", r);
    state = JSON.parse(r);
  }

  // === STEP 6: Publish ===
  if (state.step === 'Publish') {
    console.log("\n=== Step 6: Publish ===");

    r = await eval_(`
      return JSON.stringify({
        bodyPreview: document.body?.innerText?.substring(0, 1500)
      });
    `);
    console.log("Publish page:", r);

    // Click Publish Gig button
    console.log("Publishing gig...");
    r = await eval_(`
      const publishBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.includes('Publish') && !b.textContent.includes('Preview'));
      if (publishBtn) {
        publishBtn.scrollIntoView({ block: 'center' });
        publishBtn.click();
        return 'clicked publish';
      }
      return 'publish button not found';
    `);
    console.log(r);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        bodyPreview: document.body?.innerText?.substring(0, 500)
      });
    `);
    console.log("After publish:", r);
  }

  console.log("\n=== DONE ===");
  console.log("Final URL:", state.url);
  console.log("Final step:", state.step);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
