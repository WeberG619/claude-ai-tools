// Handle Fiverr Gallery (Step 5) - upload image and continue
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

  // Check page
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
      bodyPreview: document.body?.innerText?.substring(0, 1500)
    });
  `);
  console.log("Page:", r);

  const page = JSON.parse(r);

  if (page.step === 'Gallery') {
    console.log("\n=== Gallery Page ===");

    // Check what file inputs are available
    r = await eval_(`
      const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
      return JSON.stringify(fileInputs.map(f => ({
        name: f.name || '',
        accept: f.accept || '',
        class: (f.className?.toString() || '').substring(0, 60),
        parentClass: (f.parentElement?.className?.toString() || '').substring(0, 60),
        id: f.id || ''
      })));
    `);
    console.log("File inputs:", r);

    const fileInputs = JSON.parse(r);

    if (fileInputs.length > 0) {
      // Upload our gig image
      console.log("Uploading gig image...");

      // Get the file input node for DOM.setFileInputFiles
      for (let i = 0; i < fileInputs.length; i++) {
        console.log(`\nTrying file input ${i}:`, fileInputs[i]);

        const nodeResult = await send("Runtime.evaluate", {
          expression: `document.querySelectorAll('input[type="file"]')[${i}]`,
          returnByValue: false
        });

        if (nodeResult.result?.objectId) {
          const domNode = await send("DOM.describeNode", {
            objectId: nodeResult.result.objectId
          });

          if (domNode.node?.backendNodeId) {
            try {
              await send("DOM.setFileInputFiles", {
                files: ["D:\\_CLAUDE-TOOLS\\weber_profile_photo.jpg"],
                backendNodeId: domNode.node.backendNodeId
              });
              console.log("File set on input", i);

              // Dispatch change event
              await eval_(`
                const el = document.querySelectorAll('input[type="file"]')[${i}];
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('input', { bubbles: true }));
              `);

              await sleep(3000);

              // Check if it was processed
              r = await eval_(`
                const imgs = Array.from(document.querySelectorAll('img, [class*="thumbnail"], [class*="preview"]'))
                  .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 40)
                  .map(el => ({
                    tag: el.tagName,
                    src: (el.src || el.style.backgroundImage || '').substring(0, 80),
                    w: Math.round(el.getBoundingClientRect().width),
                    h: Math.round(el.getBoundingClientRect().height),
                    y: Math.round(el.getBoundingClientRect().y),
                    class: (el.className?.toString() || '').substring(0, 60)
                  }));
                const uploadStatus = Array.from(document.querySelectorAll('[class*="upload"], [class*="progress"]'))
                  .filter(el => el.offsetParent !== null)
                  .map(el => ({
                    text: el.textContent?.trim()?.substring(0, 50),
                    class: (el.className?.toString() || '').substring(0, 60)
                  }));
                return JSON.stringify({ imgs: imgs.slice(0, 5), uploadStatus: uploadStatus.slice(0, 5) });
              `);
              console.log("Upload status:", r);
            } catch(e) {
              console.log("Error:", e.message);
            }
          }
        }
      }
    }

    // Wait for upload to fully process
    await sleep(5000);

    // Check gallery state
    r = await eval_(`
      return JSON.stringify({
        bodyPreview: document.body?.innerText?.substring(0, 1000),
        errors: Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 80))
      });
    `);
    console.log("\nGallery state:", r);

    // Try saving
    console.log("\n=== Saving Gallery ===");
    r = await eval_(`
      const btn = document.querySelector('.btn-submit') ||
        Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Save & Continue'));
      if (btn) { btn.scrollIntoView({ block: 'center' }); btn.click(); }
      return btn ? btn.textContent.trim().substring(0, 30) : 'not found';
    `);
    console.log("Save:", r);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
        errors: Array.from(document.querySelectorAll('[class*="error"], [class*="validation"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 100))
      });
    `);
    console.log("After save:", r);

    const afterSave = JSON.parse(r);

    // If still on gallery with errors, might need a proper gig image (not profile photo)
    if (afterSave.step === 'Gallery') {
      console.log("\nStill on gallery. Checking requirements...");
      console.log("Errors:", afterSave.errors);

      // Try navigating to Publish directly
      console.log("Navigating to Publish...");
      await eval_(`window.location.href = location.href.replace('wizard=4', 'wizard=5').replace('tab=gallery', 'tab=publish')`);
      await sleep(5000);

      try {
        r = await eval_(`
          return JSON.stringify({
            url: location.href,
            step: document.querySelector('.current .crumb-content')?.textContent?.trim(),
            bodyPreview: document.body?.innerText?.substring(0, 500)
          });
        `);
        console.log("After navigate to publish:", r);
      } catch(e) {
        console.log("Connection lost:", e.message);
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
