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

  // Click "File Upload" button to reveal the file input
  let r = await eval_(`
    const btns = Array.from(document.querySelectorAll('button'));
    const uploadBtn = btns.find(b => b.textContent.trim() === 'File Upload');
    if (uploadBtn) { uploadBtn.click(); return 'clicked'; }
    return 'not found';
  `);
  console.log("File Upload click:", r);
  await sleep(1000);

  // Find file input and set the PDF
  await send("DOM.enable");
  const doc = await send("DOM.getDocument");

  // Try to find file input
  const result = await send("DOM.querySelectorAll", {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"]'
  });
  console.log("File inputs found:", result.nodeIds?.length || 0);

  if (result.nodeIds && result.nodeIds.length > 0) {
    // Use the first file input that accepts PDF
    for (const nodeId of result.nodeIds) {
      try {
        await send("DOM.setFileInputFiles", {
          nodeId: nodeId,
          files: ["D:\\_CLAUDE-TOOLS\\Weber_Gouin_Resume.pdf"]
        });
        console.log("File set on nodeId:", nodeId);
        break;
      } catch (e) {
        console.log("Failed nodeId", nodeId, e.message);
      }
    }

    await sleep(3000);

    // Check page state
    r = await eval_(`return document.body.innerText.substring(0, 5000)`);
    console.log("\nPage after upload:", r);

    // Look for Import and Review button
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'));
      return JSON.stringify(btns.filter(b => b.offsetParent !== null).map(b => ({
        text: b.textContent.trim().substring(0, 60),
        disabled: b.disabled
      })));
    `);
    console.log("\nButtons:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
