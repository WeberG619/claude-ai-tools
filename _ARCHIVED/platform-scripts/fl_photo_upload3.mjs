// Click the PhotoFloatingBtn to open file upload, then set file
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
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected - on photo-and-name page\n");

  // Enable DOM first so we catch dynamically created elements
  await send("DOM.enable");
  await send("DOM.getDocument");

  // Intercept file chooser dialog
  await send("Page.setInterceptFileChooserDialog", { enabled: true });
  console.log("File chooser interception enabled");

  // Click the PhotoFloatingBtn (camera icon)
  let r = await eval_(`
    const btn = document.querySelector('.PhotoFloatingBtn, [class*="PhotoFloatingBtn"]');
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, class: btn.className?.toString() });
    }
    return null;
  `);
  console.log("PhotoFloatingBtn:", r);

  if (r) {
    const pos = JSON.parse(r);
    console.log(`Clicking at (${pos.x}, ${pos.y})...`);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(2000);

    // Check what happened - modal? file dialog? new elements?
    r = await eval_(`
      const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
      const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="dialog" i], [class*="overlay" i], [class*="crop" i], [class*="popup" i]'))
        .filter(el => {
          const style = window.getComputedStyle(el);
          return style.display !== 'none' && style.visibility !== 'hidden';
        })
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 80),
          text: el.textContent?.trim()?.substring(0, 100)
        }));
      const btns = Array.from(document.querySelectorAll('button, a'))
        .filter(b => b.offsetParent !== null)
        .map(b => ({ tag: b.tagName, text: b.textContent.trim().substring(0, 40), class: b.className?.toString()?.substring(0, 60) }));
      return JSON.stringify({
        fileInputs: fileInputs.map(f => ({ id: f.id, name: f.name, accept: f.accept, class: f.className?.substring(0, 50) })),
        modals,
        buttons: btns,
        newElements: document.body.innerHTML.length,
        preview: document.body.innerText.substring(0, 1000)
      });
    `);
    console.log("\nAfter clicking PhotoFloatingBtn:", r);

    const state = JSON.parse(r);

    // If a file input appeared, use it
    if (state.fileInputs.length > 0) {
      console.log("\n=== File input found! ===");
      const evalResult = await send("Runtime.evaluate", {
        expression: `document.querySelector('input[type="file"]')`,
        returnByValue: false
      });

      if (evalResult.result?.objectId) {
        const nodeResult = await send("DOM.requestNode", {
          objectId: evalResult.result.objectId
        });

        if (nodeResult.nodeId) {
          const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
          console.log(`Uploading: ${photoPath}`);
          await send("DOM.setFileInputFiles", {
            nodeId: nodeResult.nodeId,
            files: [photoPath]
          });
          console.log("File set on input!");
          await sleep(5000);
        }
      }
    } else {
      // Maybe it opened an options menu (camera/gallery/upload)
      console.log("\nNo file input. Checking for upload option in menu...");
      r = await eval_(`
        const items = Array.from(document.querySelectorAll('*'))
          .filter(el => {
            const text = el.textContent?.trim()?.toLowerCase() || '';
            return el.offsetParent !== null && el.childElementCount === 0 &&
              (text.includes('upload') || text.includes('browse') || text.includes('choose') ||
               text.includes('gallery') || text.includes('file') || text === 'photo' || text === 'camera') &&
              text.length < 40;
          })
          .map(el => ({
            tag: el.tagName,
            text: el.textContent.trim(),
            class: el.className?.toString()?.substring(0, 60),
            rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; })()
          }));
        return JSON.stringify(items);
      `);
      console.log("Upload menu items:", r);

      const items = JSON.parse(r);
      if (items.length > 0) {
        const uploadItem = items.find(i => i.text.toLowerCase().includes('upload') || i.text.toLowerCase().includes('browse')) || items[0];
        console.log(`\nClicking "${uploadItem.text}"...`);
        await send("Input.dispatchMouseEvent", { type: "mousePressed", x: uploadItem.rect.x, y: uploadItem.rect.y, button: "left", clickCount: 1 });
        await sleep(50);
        await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: uploadItem.rect.x, y: uploadItem.rect.y, button: "left", clickCount: 1 });
        await sleep(2000);

        // Check for file input again
        r = await eval_(`
          const fi = Array.from(document.querySelectorAll('input[type="file"]'));
          return JSON.stringify({ count: fi.length });
        `);
        console.log("File inputs now:", r);
      }

      // Try alternate approach: programmatically create and trigger file input
      console.log("\nTrying programmatic approach...");
      r = await eval_(`
        // Check all inputs including hidden ones
        const allInputs = document.querySelectorAll('input');
        const fileInputs = [];
        allInputs.forEach(inp => {
          if (inp.type === 'file') fileInputs.push({
            id: inp.id, name: inp.name, accept: inp.accept,
            hidden: inp.hidden, displayNone: inp.style.display === 'none',
            parent: inp.parentElement?.className?.substring(0, 50)
          });
        });
        return JSON.stringify({ total: allInputs.length, fileInputs });
      `);
      console.log("All inputs scan:", r);
    }
  }

  // Also try clicking directly on the photo area itself
  console.log("\n--- Trying to click the photo placeholder directly ---");
  r = await eval_(`
    const photoDiv = document.querySelector('.ProfileDetailsPhotoAndName-photo');
    if (photoDiv) {
      const rect = photoDiv.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(2000);

    r = await eval_(`
      const fi = Array.from(document.querySelectorAll('input[type="file"]'));
      const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="dialog" i]'))
        .filter(el => window.getComputedStyle(el).display !== 'none')
        .map(el => el.className?.toString()?.substring(0, 60));
      return JSON.stringify({ fileInputs: fi.length, modals, preview: document.body.innerText.substring(0, 800) });
    `);
    console.log("After clicking photo area:", r);
  }

  // Final check: the page might use drag-drop or a custom overlay that dynamically creates file input
  // Try to look at ALL elements in shadow DOMs too
  r = await eval_(`
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let fileInputs = [];
    let node;
    while (node = walker.nextNode()) {
      if (node.tagName === 'INPUT' && node.type === 'file') {
        fileInputs.push({
          id: node.id, name: node.name, accept: node.accept,
          parent: node.parentElement?.tagName + '.' + node.parentElement?.className?.substring(0, 30)
        });
      }
      // Check shadow roots
      if (node.shadowRoot) {
        node.shadowRoot.querySelectorAll('input[type="file"]').forEach(f => {
          fileInputs.push({ id: f.id, name: f.name, shadowHost: node.tagName });
        });
      }
    }
    return JSON.stringify(fileInputs);
  `);
  console.log("\nDeep scan for file inputs:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
