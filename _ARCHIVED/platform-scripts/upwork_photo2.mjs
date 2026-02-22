// Upload photo to Upwork - use file chooser interception
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
  const events = [];
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.id && pending.has(msg.id)) {
      const p = pending.get(msg.id);
      pending.delete(msg.id);
      if (msg.error) p.rej(new Error(msg.error.message));
      else p.res(msg.result);
    }
    if (msg.method) {
      events.push(msg);
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
  return { ws, send, eval_, events };
}

async function clickAt(send, x, y) {
  await send("Input.dispatchMouseEvent", { type: "mouseMoved", x, y });
  await sleep(50);
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  let { ws, send, eval_, events } = await connectToPage("upwork.com");
  console.log("Connected\n");

  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });
  console.log("File chooser interception enabled");

  // First check if there's a hidden file input we can trigger
  let r = await eval_(`
    // Look for file inputs including hidden ones
    const allFileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(allFileInputs.map(el => ({
      id: el.id, accept: el.accept || '',
      hidden: el.hidden || el.style.display === 'none' || el.offsetParent === null,
      class: (el.className || '').substring(0, 50)
    })));
  `);
  console.log("All file inputs (including hidden):", r);
  const fileInputs = JSON.parse(r);

  // Click Upload photo button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Upload photo') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  console.log("Upload button:", r);
  const btn = JSON.parse(r);

  if (!btn.error) {
    await sleep(300);
    await clickAt(send, btn.x, btn.y);
    console.log("Clicked Upload photo");
    await sleep(2000);

    // Check if file chooser event fired
    const fileChooserEvents = events.filter(e => e.method === 'Page.fileChooserOpened');
    console.log("File chooser events:", fileChooserEvents.length);

    if (fileChooserEvents.length > 0) {
      await send("Page.handleFileChooser", {
        action: "accept",
        files: [photoPath]
      });
      console.log("Photo file accepted via chooser");
      await sleep(3000);
    } else {
      // Maybe a modal appeared with another upload button or file input
      console.log("No file chooser event. Checking for modal...");

      r = await eval_(`
        // Check for any new file inputs that appeared
        const newInputs = Array.from(document.querySelectorAll('input[type="file"]'));
        // Check for modal/dialog
        const modal = document.querySelector('[class*="modal"], [class*="dialog"], [role="dialog"]');
        const modalText = modal ? modal.textContent.trim().substring(0, 200) : 'no modal';
        return JSON.stringify({
          fileInputs: newInputs.length,
          fileInputDetails: newInputs.map(el => ({ accept: el.accept, hidden: !el.offsetParent })),
          modal: modalText,
          body: document.body.innerText.substring(0, 500)
        });
      `);
      console.log("After click state:", r);
      const state = JSON.parse(r);

      if (state.fileInputs > 0) {
        // Try DOM.setFileInputFiles
        console.log("Found file input, trying DOM.setFileInputFiles...");
        await send("DOM.enable");
        const doc = await send("DOM.getDocument");
        const fileNode = await send("DOM.querySelector", {
          nodeId: doc.root.nodeId,
          selector: 'input[type="file"]'
        });
        console.log("File input nodeId:", fileNode.nodeId);

        if (fileNode.nodeId > 0) {
          await send("DOM.setFileInputFiles", {
            nodeId: fileNode.nodeId,
            files: [photoPath]
          });
          console.log("File set on input");
          await sleep(3000);

          // Check for file chooser events after setting
          const newEvents = events.filter(e => e.method === 'Page.fileChooserOpened');
          if (newEvents.length > fileChooserEvents.length) {
            await send("Page.handleFileChooser", {
              action: "accept",
              files: [photoPath]
            });
            console.log("Handled file chooser after DOM set");
          }

          // Trigger events
          await eval_(`
            const inp = document.querySelector('input[type="file"]');
            if (inp) {
              inp.dispatchEvent(new Event('change', { bubbles: true }));
              inp.dispatchEvent(new Event('input', { bubbles: true }));
            }
          `);
          await sleep(3000);
        }
      }

      // Try clicking the file input directly via JS
      if (state.fileInputs > 0) {
        console.log("Trying JS click on file input...");
        await eval_(`
          const inp = document.querySelector('input[type="file"]');
          if (inp) inp.click();
        `);
        await sleep(2000);

        const newChooserEvents = events.filter(e => e.method === 'Page.fileChooserOpened');
        console.log("File chooser events after JS click:", newChooserEvents.length);
        if (newChooserEvents.length > 0) {
          await send("Page.handleFileChooser", {
            action: "accept",
            files: [photoPath]
          });
          console.log("Photo accepted!");
          await sleep(3000);
        }
      }
    }
  }

  // Check photo status
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
      .map(el => el.textContent.trim().substring(0, 80));
    const imgs = Array.from(document.querySelectorAll('img'))
      .filter(el => el.offsetParent !== null && el.src && !el.src.includes('icon') && el.getBoundingClientRect().width > 50)
      .map(el => ({ src: el.src.substring(0, 60), w: el.width, h: el.height }));
    return JSON.stringify({ errors, imgs });
  `);
  console.log("\nPhoto result:", r);

  // Disable interception
  try { await send("Page.setInterceptFileChooserDialog", { enabled: false }); } catch(e) {}

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
