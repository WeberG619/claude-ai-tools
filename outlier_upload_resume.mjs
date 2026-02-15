const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Tab not found for: ${urlMatch}`);
  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
  let id = 1;
  const pending = new Map();
  ws.addEventListener("message", e => {
    const m = JSON.parse(e.data);
    if (m.id && pending.has(m.id)) {
      const p = pending.get(m.id);
      pending.delete(m.id);
      if (m.error) p.rej(new Error(m.error.message));
      else p.res(m.result);
    }
  });
  const send = (method, params = {}) => new Promise((res, rej) => {
    const i = id++;
    pending.set(i, { res, rej });
    ws.send(JSON.stringify({ id: i, method, params }));
  });
  const eval_ = async (expr) => {
    const r = await send("Runtime.evaluate", {
      expression: `(async () => { ${expr} })()`,
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

(async () => {
  let { ws, send, eval_ } = await connectToPage("outlier");

  // First click the "File Upload" button for resume to see if it reveals a file input
  let r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    const uploadBtn = btns.find(b => b.textContent.includes('File Upload') && !b.textContent.includes('disabled'));
    if (uploadBtn) {
      // Check for hidden file inputs near this button
      const parent = uploadBtn.closest('div');
      const fileInput = parent ? parent.querySelector('input[type="file"]') : null;
      if (fileInput) {
        return JSON.stringify({ type: 'file-input-found', accept: fileInput.accept });
      }
      const rect = uploadBtn.getBoundingClientRect();
      return JSON.stringify({ type: 'button', x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return 'not found';
  `);
  console.log("Upload button:", r);

  // Check for any file inputs on the page
  r = await eval_(`
    const fileInputs = document.querySelectorAll('input[type="file"]');
    return JSON.stringify(Array.from(fileInputs).map((fi, i) => ({
      idx: i,
      name: fi.name,
      accept: fi.accept,
      hidden: fi.offsetParent === null,
      id: fi.id
    })));
  `);
  console.log("File inputs:", r);

  // Click the File Upload button
  r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    // Find the second "File Upload" button (first might be LinkedIn)
    const uploadBtns = btns.filter(b => b.textContent.trim() === 'File Upload');
    const resumeBtn = uploadBtns[0]; // Should be the resume one
    if (resumeBtn) {
      resumeBtn.click();
      return 'clicked File Upload';
    }
    return 'not found';
  `);
  console.log("JS click:", r);
  await sleep(1000);

  // Check for file inputs again after click
  r = await eval_(`
    const fileInputs = document.querySelectorAll('input[type="file"]');
    return JSON.stringify(Array.from(fileInputs).map((fi, i) => ({
      idx: i,
      name: fi.name,
      accept: fi.accept,
      hidden: fi.offsetParent === null
    })));
  `);
  console.log("File inputs after click:", r);

  // Try to find and use the file input with DOM.setFileInputFiles
  r = await eval_(`
    const fi = document.querySelector('input[type="file"]');
    if (fi) return 'found';
    return 'not found';
  `);

  if (r === 'found') {
    // Get the node ID for the file input
    await send("DOM.enable");
    const doc = await send("DOM.getDocument");
    const result = await send("DOM.querySelector", {
      nodeId: doc.root.nodeId,
      selector: 'input[type="file"]'
    });

    if (result.nodeId) {
      console.log("File input nodeId:", result.nodeId);
      // Set the file - use Windows path for Chrome
      try {
        await send("DOM.setFileInputFiles", {
          nodeId: result.nodeId,
          files: ["D:\\_CLAUDE-TOOLS\\Weber_Gouin_Resume.txt"]
        });
        console.log("File set successfully!");
        await sleep(3000);

        // Check page state
        r = await eval_(`return document.body.innerText.substring(0, 3000)`);
        console.log("\nPage after upload:", r);
      } catch (e) {
        console.log("File set error:", e.message);
      }
    }
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
