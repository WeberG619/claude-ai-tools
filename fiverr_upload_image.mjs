// Fiverr gallery image upload - deep investigation
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
    // Forward to event handlers
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

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_, onEvent } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  // Check we're on gallery
  let r = await eval_(`return JSON.stringify({ url: location.href, step: document.querySelector('.current .crumb-content')?.textContent?.trim() })`);
  console.log("Current:", r);

  // Deep inspection of the gallery page upload areas
  console.log("\n=== Gallery Upload Areas ===");
  r = await eval_(`
    // Find all file inputs (even hidden ones)
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    const fileInputInfo = fileInputs.map(f => ({
      id: f.id || '',
      name: f.name || '',
      accept: f.accept || '',
      class: (f.className?.toString() || '').substring(0, 60),
      parentTag: f.parentElement?.tagName,
      parentClass: (f.parentElement?.className?.toString() || '').substring(0, 60),
      display: window.getComputedStyle(f).display,
      visibility: window.getComputedStyle(f).visibility,
      opacity: window.getComputedStyle(f).opacity,
      rect: {
        x: Math.round(f.getBoundingClientRect().x),
        y: Math.round(f.getBoundingClientRect().y),
        w: Math.round(f.getBoundingClientRect().width),
        h: Math.round(f.getBoundingClientRect().height)
      }
    }));

    // Find all upload/drop zones
    const uploadZones = Array.from(document.querySelectorAll('[class*="upload"], [class*="drop"], [class*="dropzone"]'))
      .filter(el => el.offsetParent !== null || el.getBoundingClientRect().width > 0)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        text: el.textContent?.trim()?.substring(0, 60),
        rect: {
          x: Math.round(el.getBoundingClientRect().x),
          y: Math.round(el.getBoundingClientRect().y),
          w: Math.round(el.getBoundingClientRect().width),
          h: Math.round(el.getBoundingClientRect().height)
        }
      }));

    // Find elements with "Browse" text
    const browseEls = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.trim() === 'Browse' && el.children.length === 0)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        parentTag: el.parentElement?.tagName,
        parentClass: (el.parentElement?.className?.toString() || '').substring(0, 60),
        y: Math.round(el.getBoundingClientRect().y),
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        visible: el.offsetParent !== null
      }));

    return JSON.stringify({ fileInputs: fileInputInfo, uploadZones: uploadZones.slice(0, 10), browseEls });
  `);
  console.log(r);

  const info = JSON.parse(r);
  console.log("\nFile inputs:", info.fileInputs.length);
  info.fileInputs.forEach((f, i) => console.log(`  ${i}: id=${f.id} accept=${f.accept} display=${f.display} rect=${JSON.stringify(f.rect)}`));
  console.log("Upload zones:", info.uploadZones.length);
  info.uploadZones.forEach((u, i) => console.log(`  ${i}: ${u.class.substring(0, 40)} text="${u.text?.substring(0, 30)}" y=${u.rect.y}`));
  console.log("Browse elements:", info.browseEls.length);
  info.browseEls.forEach((b, i) => console.log(`  ${i}: ${b.tag} visible=${b.visible} y=${b.y} parent=${b.parentTag}.${b.parentClass?.substring(0, 30)}`));

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });

  // Listen for file chooser events
  let chooserPromiseResolve;
  const chooserPromise = new Promise(r => chooserPromiseResolve = r);
  onEvent(async (msg) => {
    if (msg.method === 'Page.fileChooserOpened') {
      console.log("\n>>> File chooser opened! Mode:", msg.params?.mode);
      try {
        await send("Page.handleFileChooser", {
          action: "accept",
          files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig_image.jpg"]
        });
        console.log(">>> File provided successfully!");
        chooserPromiseResolve(true);
      } catch(e) {
        console.log(">>> Error providing file:", e.message);
        chooserPromiseResolve(false);
      }
    }
  });

  // Try approach 1: Click the image file input directly
  const imageInput = info.fileInputs.find(f => f.id === 'image');
  if (imageInput) {
    console.log("\n=== Approach 1: Click #image file input ===");
    // Make it visible and click
    await eval_(`
      const el = document.querySelector('#image');
      el.style.display = 'block';
      el.style.position = 'fixed';
      el.style.top = '100px';
      el.style.left = '100px';
      el.style.width = '200px';
      el.style.height = '50px';
      el.style.opacity = '1';
      el.style.zIndex = '99999';
    `);
    await sleep(300);

    r = await eval_(`
      const el = document.querySelector('#image');
      const rect = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2), w: Math.round(rect.width) });
    `);
    console.log("Image input coords:", r);
    const inputCoords = JSON.parse(r);
    await clickAt(send, inputCoords.x, inputCoords.y);

    // Wait for file chooser
    const result = await Promise.race([
      chooserPromise,
      sleep(5000).then(() => 'timeout')
    ]);
    console.log("File chooser result:", result);

    // Reset input visibility
    await eval_(`
      const el = document.querySelector('#image');
      el.style.display = '';
      el.style.position = '';
      el.style.top = '';
      el.style.left = '';
      el.style.width = '';
      el.style.height = '';
      el.style.opacity = '';
      el.style.zIndex = '';
    `);

    if (result === true) {
      console.log("Upload successful! Waiting for processing...");
      await sleep(8000);

      r = await eval_(`
        const errors = Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
          .map(el => el.textContent.trim().substring(0, 80));
        const hasImage = document.body?.innerText?.includes('fiverr_gig_image');
        return JSON.stringify({ errors, hasImage, bodySnippet: document.body?.innerText?.substring(0, 800) });
      `);
      console.log("Status:", r);
    }
  }

  // If approach 1 didn't work, try approach 2: Click Browse text
  if (info.browseEls.length > 0) {
    const imgBrowse = info.browseEls.find(b => b.visible && b.y > 500) || info.browseEls[1];
    if (imgBrowse) {
      console.log(`\n=== Approach 2: Click Browse at (${imgBrowse.x}, ${imgBrowse.y}) ===`);
      await clickAt(send, imgBrowse.x, imgBrowse.y);

      const result2 = await Promise.race([
        new Promise(r => {
          onEvent(async (msg) => {
            if (msg.method === 'Page.fileChooserOpened') {
              await send("Page.handleFileChooser", {
                action: "accept",
                files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig_image.jpg"]
              });
              r(true);
            }
          });
        }),
        sleep(5000).then(() => 'timeout')
      ]);
      console.log("Browse click result:", result2);
    }
  }

  // Clean up
  try {
    await send("Page.setInterceptFileChooserDialog", { enabled: false });
  } catch(e) {}

  // Check final state
  await sleep(3000);
  r = await eval_(`
    return JSON.stringify({
      errors: Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0)
        .map(el => el.textContent.trim().substring(0, 80)),
      bodyPreview: document.body?.innerText?.substring(0, 800)
    });
  `);
  console.log("\nFinal gallery state:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
