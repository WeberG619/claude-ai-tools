// Upload profile photo to Upwork using DOM.setFileInputFiles
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
import fs from 'fs';
import path from 'path';

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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Find file input for photo
  let r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'))
      .map(el => ({
        id: el.id, name: el.name || '',
        accept: el.accept || '',
        class: (el.className || '').substring(0, 50),
        parentText: (el.parentElement?.textContent || '').trim().substring(0, 40)
      }));
    return JSON.stringify(fileInputs);
  `);
  console.log("File inputs:", r);
  const fileInputs = JSON.parse(r);

  // Try to find photo-specific file input
  const photoInput = fileInputs.find(f => f.accept.includes('image') || f.parentText.includes('photo') || f.parentText.includes('Upload'));

  // Enable DOM domain
  await send("DOM.enable");
  await send("DOM.getDocument");

  // Find the file input node
  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

  // Check if file exists
  const exists = fs.existsSync("/mnt/d/007 - DOCUMENTS TO BE FILED/Weber Files/Weber's Photo.jpg");
  console.log("Photo file exists:", exists);

  if (exists) {
    // Try to use Page.setInterceptFileChooserDialog
    await send("Page.setInterceptFileChooserDialog", { enabled: true });
    console.log("File chooser interception enabled");

    // Listen for file chooser
    let fileChooserReceived = false;
    const originalHandler = ws.onmessage;

    // Set up event listener for fileChooserOpened
    const fileChooserPromise = new Promise((resolve) => {
      const handler = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === 'Page.fileChooserOpened') {
          fileChooserReceived = true;
          resolve(msg.params);
        }
      };
      ws.addEventListener("message", handler);
      setTimeout(() => resolve(null), 5000); // timeout after 5s
    });

    // Click Upload photo button
    r = await eval_(`
      const uploadBtn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim().includes('Upload photo') && b.offsetParent !== null);
      if (uploadBtn) {
        const rect = uploadBtn.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      // Try clicking the photo area
      const photoArea = document.querySelector('[class*="photo"], [class*="avatar"], [data-test*="photo"]');
      if (photoArea) {
        const rect = photoArea.getBoundingClientRect();
        return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
      }
      return JSON.stringify({ error: 'no upload button' });
    `);
    console.log("Upload button:", r);
    const btn = JSON.parse(r);
    if (!btn.error) {
      await clickAt(send, btn.x, btn.y);
      console.log("Clicked upload button");
    }

    // Wait for file chooser
    const chooser = await fileChooserPromise;
    console.log("File chooser:", chooser ? "received" : "not received");

    if (chooser) {
      // Handle the file chooser
      await send("Page.handleFileChooser", {
        action: "accept",
        files: [photoPath]
      });
      console.log("File selected via chooser");
      await sleep(3000);
    } else {
      // Fallback: try DOM.setFileInputFiles on the first file input
      console.log("Trying DOM.setFileInputFiles approach...");

      // Get the file input's node ID
      r = await send("DOM.querySelector", {
        nodeId: (await send("DOM.getDocument")).root.nodeId,
        selector: 'input[type="file"]'
      });
      console.log("File input node:", JSON.stringify(r));

      if (r.nodeId > 0) {
        await send("DOM.setFileInputFiles", {
          nodeId: r.nodeId,
          files: [photoPath]
        });
        console.log("Files set on input");
        await sleep(3000);

        // Trigger change event
        await eval_(`
          const inp = document.querySelector('input[type="file"]');
          if (inp) {
            inp.dispatchEvent(new Event('change', { bubbles: true }));
          }
        `);
        await sleep(2000);
      }
    }

    // Check if photo was uploaded
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
        .map(el => el.textContent.trim().substring(0, 80));
      const img = document.querySelector('[class*="photo"] img, [class*="avatar"] img');
      return JSON.stringify({ errors, hasImg: !!img, imgSrc: img ? img.src.substring(0, 60) : 'none' });
    `);
    console.log("Photo status:", r);

    // Try disabling file chooser interception
    try {
      await send("Page.setInterceptFileChooserDialog", { enabled: false });
    } catch(e) {}
  }

  // Check final state and try Review
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
      .map(el => el.textContent.trim().substring(0, 100));
    return JSON.stringify(errors);
  `);
  console.log("\nAll errors:", r);

  // Try Review
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Review') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  await sleep(300);
  const reviewBtn = JSON.parse(r);
  if (!reviewBtn.error) {
    await clickAt(send, reviewBtn.x, reviewBtn.y);
    console.log("Clicked Review");
    await sleep(5000);

    r = await eval_(`return JSON.stringify({
      url: location.href, step: location.href.split('/').pop().split('?')[0],
      body: document.body.innerText.substring(0, 500)
    })`);
    const page = JSON.parse(r);
    console.log("\nPage:", page.step);
    console.log(page.body.substring(0, 300));
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
