// Upload photo: click button, wait for input, set files, trigger events
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
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

  // Enable DOM first
  await send("DOM.enable");

  // First, re-set the form fields that may have been cleared
  let r = await eval_(`
    const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    const fields = [
      ['mm/dd/yyyy', '03/18/1974'],
      ['Enter street address', '619 Hopkins Rd'],
      ['Enter city', 'Sandpoint'],
      ['Enter state/province', 'ID'],
      ['Enter ZIP/Postal code', '83864'],
      ['Enter number', '2083551234']
    ];
    for (const [ph, val] of fields) {
      const inp = Array.from(document.querySelectorAll('input')).find(el => el.placeholder === ph);
      if (inp && !inp.value) {
        setter.call(inp, val);
        inp.dispatchEvent(new Event('input', { bubbles: true }));
        inp.dispatchEvent(new Event('change', { bubbles: true }));
      }
    }
    return 'fields set';
  `);
  console.log(r);

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });

  // Create a promise that resolves when file chooser opens
  let fileChooserResolve;
  const fileChooserPromise = new Promise(resolve => {
    fileChooserResolve = resolve;
    setTimeout(() => resolve(null), 8000);
  });

  // Listen for the event
  const originalOnMessage = ws.onmessage;
  ws.addEventListener("message", (event) => {
    const msg = JSON.parse(event.data);
    if (msg.method === 'Page.fileChooserOpened') {
      console.log("FILE CHOOSER EVENT:", JSON.stringify(msg.params));
      fileChooserResolve(msg.params);
    }
  });

  // Click Upload photo button
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Upload photo'));
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  const uploadBtn = JSON.parse(r);
  if (!uploadBtn.error) {
    await clickAt(send, uploadBtn.x, uploadBtn.y);
    console.log("Clicked Upload photo, waiting for file input...");
  }

  await sleep(1500);

  // Check if file input appeared
  r = await eval_(`
    const inp = document.querySelector('input[type="file"]');
    return inp ? 'found file input' : 'no file input';
  `);
  console.log("File input:", r);

  // If file input exists, try to click it to open chooser
  if (r === 'found file input') {
    console.log("Clicking file input via JS...");
    await eval_(`
      const inp = document.querySelector('input[type="file"]');
      if (inp) inp.click();
    `);

    const chooserParams = await fileChooserPromise;
    if (chooserParams) {
      console.log("Got file chooser! Handling...");
      await send("Page.handleFileChooser", {
        action: "accept",
        files: [photoPath]
      });
      console.log("File accepted!");
      await sleep(5000);
    } else {
      console.log("No file chooser event. Using DOM.setFileInputFiles fallback...");

      // Re-get document and find file input
      const doc = await send("DOM.getDocument", { depth: -1 });
      const result = await send("Runtime.evaluate", {
        expression: `document.querySelector('input[type="file"]') ? 'exists' : 'none'`,
        returnByValue: true
      });
      console.log("Input exists:", result.result?.value);

      // Try using Runtime.evaluate to get a remote object, then use it with DOM
      const objResult = await send("Runtime.evaluate", {
        expression: `document.querySelector('input[type="file"]')`,
        returnByValue: false
      });
      console.log("Object:", JSON.stringify(objResult.result));

      if (objResult.result?.objectId) {
        // Use DOM.setFileInputFiles with backendNodeId
        const nodeDesc = await send("DOM.describeNode", {
          objectId: objResult.result.objectId
        });
        console.log("Node backendNodeId:", nodeDesc.node?.backendNodeId);

        if (nodeDesc.node?.backendNodeId) {
          await send("DOM.setFileInputFiles", {
            backendNodeId: nodeDesc.node.backendNodeId,
            files: [photoPath]
          });
          console.log("Files set via backendNodeId!");
          await sleep(5000);
        }
      }
    }
  }

  // Check result
  r = await eval_(`
    const imgs = Array.from(document.querySelectorAll('img'))
      .filter(el => el.getBoundingClientRect().width > 50 && el.src && !el.src.includes('icon'))
      .map(el => ({ src: el.src.substring(0, 80), w: Math.round(el.getBoundingClientRect().width) }));
    const canvas = document.querySelector('canvas');
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
      .map(el => el.textContent.trim().substring(0, 80));
    const body = document.body.innerText.substring(0, 300);
    return JSON.stringify({ imgs, hasCanvas: !!canvas, errors, body });
  `);
  console.log("\nResult:", r);
  const result = JSON.parse(r);

  // If crop tool appeared, save it
  if (result.hasCanvas || result.imgs.length > 0) {
    console.log("Photo loaded! Looking for save button...");
    r = await eval_(`
      const btns = Array.from(document.querySelectorAll('button'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({ text: el.textContent.trim().substring(0, 30), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
      return JSON.stringify(btns);
    `);
    console.log("Buttons:", r);
    const btns = JSON.parse(r);
    const save = btns.find(b => b.text.includes('Save') || b.text.includes('Done') || b.text.includes('Apply') || b.text.includes('Crop'));
    if (save) {
      await clickAt(send, save.x, save.y);
      console.log(`Clicked: ${save.text}`);
      await sleep(3000);
    }
  }

  // Disable interception
  try { await send("Page.setInterceptFileChooserDialog", { enabled: false }); } catch(e) {}

  // Try Review
  await sleep(1000);
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 3)
      .map(el => el.textContent.trim().substring(0, 80));
    return JSON.stringify(errors);
  `);
  console.log("\nAll errors:", r);

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
    r = await eval_(`return JSON.stringify({ url: location.href, step: location.href.split('/').pop().split('?')[0], body: document.body.innerText.substring(0, 300) })`);
    console.log("\nAfter Review:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
