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

(async () => {
  let { ws, send, eval_ } = await connectToPage("fiverr");

  // Enable DOM
  await send("DOM.enable");

  // Get the file input
  const doc = await send("DOM.getDocument");
  const fileInputNode = await send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: 'input[name="profile[image]"]'
  });
  console.log("File input node:", JSON.stringify(fileInputNode));

  if (fileInputNode.nodeId) {
    // Set the file on the input
    await send("DOM.setFileInputFiles", {
      nodeId: fileInputNode.nodeId,
      files: ["D:\\_CLAUDE-TOOLS\\weber_profile_pic.jpg"]
    });
    console.log("File set on input!");

    await sleep(5000);

    // Check if there's a crop/save dialog
    let r = await eval_(`return document.body.innerText.substring(0, 3000)`);
    console.log("\nPage after upload:", r);

    // Look for save/crop buttons
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null);
      return JSON.stringify(btns.map(b => ({
        text: b.textContent.trim().substring(0, 40),
        disabled: b.disabled,
        rect: (() => { const r = b.getBoundingClientRect(); return { x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2) }; })()
      })));
    `);
    console.log("\nButtons:", r);

    // Check for modal/dialog
    r = await eval_(`
      const modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"]');
      return JSON.stringify(Array.from(modals).filter(m => m.offsetParent !== null).map(m => ({
        tag: m.tagName,
        classes: (typeof m.className === 'string' ? m.className : '').substring(0, 60),
        text: m.textContent?.trim().substring(0, 200)
      })));
    `);
    console.log("\nModals:", r);
  }

  ws.close();
})().catch(e => console.error("Error:", e.message));
