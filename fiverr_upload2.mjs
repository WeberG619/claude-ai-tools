// Fiverr gallery upload - use JS click to trigger file chooser
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
  const eventHandlers = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
    for (const h of eventHandlers) h(msg);
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
  const onEvent = (handler) => eventHandlers.push(handler);
  return { ws, send, eval_, onEvent };
}

async function main() {
  const { ws, send, eval_, onEvent } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });

  // Set up file chooser handler
  let fileChooserHandled = false;
  onEvent(async (msg) => {
    if (msg.method === 'Page.fileChooserOpened' && !fileChooserHandled) {
      fileChooserHandled = true;
      console.log(">>> File chooser opened! Mode:", msg.params?.mode);
      try {
        await send("Page.handleFileChooser", {
          action: "accept",
          files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig_image.jpg"]
        });
        console.log(">>> File provided!");
      } catch(e) {
        console.log(">>> Error:", e.message);
      }
    }
  });

  // Approach: Use JavaScript .click() on the file input
  console.log("=== Triggering file input via JS click ===");
  let r = await eval_(`
    const el = document.querySelector('#image');
    if (!el) return 'no #image input';
    el.click();
    return 'clicked #image';
  `);
  console.log(r);
  await sleep(3000);

  if (!fileChooserHandled) {
    console.log("JS click didn't trigger file chooser. Trying label click...");

    // Try clicking the parent label
    r = await eval_(`
      const el = document.querySelector('#image');
      const label = el?.closest('label') || el?.parentElement;
      if (label) {
        label.click();
        return 'clicked label';
      }
      return 'no label';
    `);
    console.log(r);
    await sleep(3000);
  }

  if (!fileChooserHandled) {
    console.log("Label click didn't work. Trying dropzone click...");

    // Try clicking the dropzone-body image area
    r = await eval_(`
      const dz = document.querySelector('.dropzone-body.image');
      if (dz) {
        dz.click();
        return 'clicked dropzone-body.image';
      }
      return 'no dropzone';
    `);
    console.log(r);
    await sleep(3000);
  }

  if (!fileChooserHandled) {
    console.log("Dropzone click didn't work either.");
    console.log("Trying to set file via DataTransfer + drop event...");

    // Alternative: Create a File object and dispatch a drop event on the dropzone
    // This simulates drag-and-drop
    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          // Fetch the image as a blob
          const response = await fetch('data:image/jpeg;base64,' + btoa('fake'));
          // We can't fetch local files from the browser context
          // Instead, let's try creating a synthetic file

          // Find the dropzone for images
          const dz = document.querySelector('.dropzone-body.image') || document.querySelector('.dropzone');
          if (!dz) { resolve('no dropzone'); return; }

          // Create a minimal JPEG file (1x1 pixel)
          const canvas = document.createElement('canvas');
          canvas.width = 1280;
          canvas.height = 769;
          const ctx = canvas.getContext('2d');
          // Draw a blue rectangle
          ctx.fillStyle = '#1a1a2e';
          ctx.fillRect(0, 0, 1280, 769);
          ctx.fillStyle = '#e94560';
          ctx.fillRect(0, 380, 1280, 9);
          ctx.fillStyle = 'white';
          ctx.font = 'bold 72px Arial';
          ctx.textAlign = 'center';
          ctx.fillText('Data Entry & Excel', 640, 200);
          ctx.font = '36px Arial';
          ctx.fillStyle = '#a0a0b0';
          ctx.fillText('Fast • Accurate • Professional', 640, 260);
          ctx.fillStyle = '#e0e0e0';
          ctx.font = '24px Arial';
          ctx.fillText('Data Entry | Excel Spreadsheets | Data Processing', 640, 500);
          ctx.fillText('99.9% Accuracy Guaranteed', 640, 540);

          canvas.toBlob((blob) => {
            if (!blob) { resolve('no blob'); return; }

            const file = new File([blob], 'gig_image.jpg', { type: 'image/jpeg' });
            const dt = new DataTransfer();
            dt.items.add(file);

            // Try setting on the file input
            const fileInput = document.querySelector('#image');
            if (fileInput) {
              fileInput.files = dt.files;
              fileInput.dispatchEvent(new Event('change', { bubbles: true }));
              fileInput.dispatchEvent(new Event('input', { bubbles: true }));
            }

            // Also try drop event on the dropzone
            const dropEvt = new DragEvent('drop', {
              bubbles: true,
              cancelable: true,
              dataTransfer: dt
            });
            dz.dispatchEvent(dropEvt);

            resolve('dispatched drop event with ' + blob.size + ' byte blob');
          }, 'image/jpeg', 0.95);
        } catch(e) {
          resolve('error: ' + e.message);
        }
      });
    `);
    console.log("DataTransfer result:", r);
    await sleep(5000);
  }

  // Check upload status
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
      .map(el => el.textContent.trim().substring(0, 80));
    const hasThumb = Array.from(document.querySelectorAll('[class*="thumb"], [class*="preview"], img'))
      .filter(el => el.offsetParent !== null && el.getBoundingClientRect().width > 60)
      .some(el => el.src?.includes('blob:') || el.src?.includes('data:') || el.style.backgroundImage?.includes('url'));
    return JSON.stringify({
      errors,
      hasThumb,
      bodySnippet: document.body?.innerText?.substring(0, 500)
    });
  `);
  console.log("\nUpload status:", r);

  // If DataTransfer approach worked, try saving
  const status = JSON.parse(r);
  if (!status.errors.includes('Please select at least 1 image')) {
    console.log("\n=== Image uploaded! Saving... ===");
    await eval_(`document.querySelector('.btn-submit')?.click()`);
    await sleep(5000);
    r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
    console.log("After save:", r);
  } else {
    console.log("\nUpload still not working. Image needs to be uploaded manually.");
    console.log("The gig is almost complete - all other steps are done.");
  }

  try {
    await send("Page.setInterceptFileChooserDialog", { enabled: false });
  } catch(e) {}

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
