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
  console.log("File input node:", fileInputNode.nodeId);

  // Set files using CDP
  await send("DOM.setFileInputFiles", {
    nodeId: fileInputNode.nodeId,
    files: ["D:\\_CLAUDE-TOOLS\\weber_profile_pic.jpg"]
  });
  console.log("Files set!");

  // Dispatch change event manually via JS
  let r = await eval_(`
    const input = document.querySelector('input[name="profile[image]"]');
    if (input && input.files && input.files.length > 0) {
      console.log('File found:', input.files[0].name, input.files[0].size);
      // Dispatch change event
      input.dispatchEvent(new Event('change', { bubbles: true }));
      input.dispatchEvent(new Event('input', { bubbles: true }));
      return 'dispatched change, file: ' + input.files[0].name + ' size: ' + input.files[0].size;
    }
    return 'no file on input';
  `);
  console.log("Change event:", r);

  await sleep(5000);

  // Check for crop dialog or upload result
  r = await eval_(`
    // Check for modals, overlays, crop dialogs
    const modals = document.querySelectorAll('[class*="modal"], [class*="Modal"], [role="dialog"], [class*="crop"], [class*="Crop"], [class*="overlay"], [class*="Overlay"]');
    const visible = Array.from(modals).filter(m => {
      const style = window.getComputedStyle(m);
      return style.display !== 'none' && style.visibility !== 'hidden';
    });
    return JSON.stringify(visible.map(m => ({
      tag: m.tagName,
      classes: (typeof m.className === 'string' ? m.className : '').substring(0, 80),
      text: m.textContent?.trim().substring(0, 200)
    })));
  `);
  console.log("\nVisible modals/overlays:", r);

  // Check if avatar image changed
  r = await eval_(`
    const img = document.querySelector('.profile-pict-img, img[class*="profile"], img[class*="avatar"]');
    if (img) return img.src;
    return 'no img found';
  `);
  console.log("\nAvatar img src:", r);

  // Check all images on page for profile area
  r = await eval_(`
    const container = document.querySelector('.user-profile-image, .profile-pict');
    if (container) {
      return container.innerHTML.substring(0, 500);
    }
    return 'no container';
  `);
  console.log("\nProfile pic container HTML:", r);

  ws.close();
})().catch(e => console.error("Error:", e.message));
