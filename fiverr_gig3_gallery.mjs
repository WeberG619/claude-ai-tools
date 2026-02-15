// Upload gig #3 gallery image (wizard=4) and save
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

  // Verify on wizard=4
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard')
    });
  `);
  console.log("State:", r);

  // === UPLOAD IMAGE ===
  console.log("=== Upload Image ===");

  // Enable DOM domain
  await send("DOM.enable");

  // Find the file input
  r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(fileInputs.map((el, i) => ({
      idx: i,
      id: el.id,
      name: el.name,
      accept: el.accept,
      class: el.className.substring(0, 50),
      visible: el.offsetParent !== null
    })));
  `);
  console.log("File inputs:", r);

  // Get the DOM node for the file input
  const docResult = await send("DOM.getDocument", { depth: 0 });
  const rootNodeId = docResult.root.nodeId;

  // Find file input by selector
  let fileNodeId;
  try {
    const qResult = await send("DOM.querySelector", {
      nodeId: rootNodeId,
      selector: 'input[type="file"]'
    });
    fileNodeId = qResult.nodeId;
    console.log("File input node ID:", fileNodeId);
  } catch (e) {
    console.log("querySelector failed, trying alternative...");
    // Try finding by ID
    const qResult = await send("DOM.querySelector", {
      nodeId: rootNodeId,
      selector: '#image'
    });
    fileNodeId = qResult.nodeId;
    console.log("File input node ID (by #image):", fileNodeId);
  }

  if (fileNodeId && fileNodeId > 0) {
    // Set the file using Windows path
    await send("DOM.setFileInputFiles", {
      nodeId: fileNodeId,
      files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"]
    });
    console.log("File set on input");
    await sleep(5000);

    // Check if image appeared
    r = await eval_(`
      const imgs = Array.from(document.querySelectorAll('img[src*="blob:"], img[src*="fiverr"], .image-preview, [class*="upload"], [class*="gallery"]'));
      return JSON.stringify(imgs.map(el => ({
        tag: el.tagName,
        src: (el.src || '').substring(0, 80),
        class: (el.className || '').substring(0, 50),
        w: el.offsetWidth,
        h: el.offsetHeight
      })));
    `);
    console.log("After upload:", r);
  } else {
    console.log("ERROR: Could not find file input node");
  }

  // Wait for upload to process
  await sleep(3000);

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
  console.log("Save button:", r);
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
    await sleep(10000);

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

    // Navigate to wizard=5 if needed
    const state = JSON.parse(r);
    if (state.wizard === '4' && state.errors.length === 0) {
      console.log("Navigating to wizard=5...");
      await eval_(`window.location.href = location.href.replace(/wizard=4/, 'wizard=5').replace(/&tab=\\w+/, '')`);
      await sleep(5000);
      ws.close();
      await sleep(1000);
      ({ ws, send, eval_ } = await connectToPage("manage_gigs"));
      r = await eval_(`return JSON.stringify({ url: location.href, wizard: new URL(location.href).searchParams.get('wizard') })`);
      console.log("Nav to wizard=5:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
