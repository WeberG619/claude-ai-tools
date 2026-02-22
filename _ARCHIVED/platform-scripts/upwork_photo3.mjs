// Upload photo via DOM.setFileInputFiles without interception
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

  // Click Upload photo
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim().includes('Upload photo') && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(rect.x + rect.width/2), y: Math.round(rect.y + rect.height/2) });
    }
    return JSON.stringify({ error: 'none' });
  `);
  const btn = JSON.parse(r);
  if (!btn.error) {
    await clickAt(send, btn.x, btn.y);
    console.log("Clicked Upload photo");
    await sleep(1500);
  }

  // Enable DOM
  await send("DOM.enable");
  const doc = await send("DOM.getDocument");

  // Find file input
  const fileNode = await send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: 'input[type="file"][accept="image/*"]'
  });
  console.log("File input nodeId:", fileNode.nodeId);

  if (fileNode.nodeId > 0) {
    // Set the file
    await send("DOM.setFileInputFiles", {
      nodeId: fileNode.nodeId,
      files: [photoPath]
    });
    console.log("File set via DOM.setFileInputFiles");

    // Wait for upload processing
    await sleep(5000);

    // Check state
    r = await eval_(`
      const inp = document.querySelector('input[type="file"][accept="image/*"]');
      const files = inp ? inp.files : null;
      const hasFiles = files && files.length > 0;
      const fileName = hasFiles ? files[0].name : 'none';
      const fileSize = hasFiles ? files[0].size : 0;

      // Check for upload preview
      const imgs = Array.from(document.querySelectorAll('img'))
        .filter(el => el.getBoundingClientRect().width > 50 && el.getBoundingClientRect().height > 50)
        .map(el => ({ src: el.src.substring(0, 80), w: Math.round(el.getBoundingClientRect().width), h: Math.round(el.getBoundingClientRect().height) }));

      // Check for canvas (crop tool)
      const canvas = document.querySelector('canvas');

      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
        .map(el => el.textContent.trim().substring(0, 80));

      return JSON.stringify({ hasFiles, fileName, fileSize, imgs, hasCanvas: !!canvas, errors });
    `);
    console.log("After file set:", r);
    const state = JSON.parse(r);

    // If there's a crop tool (canvas), look for save/confirm button
    if (state.hasCanvas) {
      console.log("Crop tool detected!");
      r = await eval_(`
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 30)
          .map(el => ({ text: el.textContent.trim(), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
        return JSON.stringify(btns);
      `);
      console.log("Buttons:", r);
      const btns = JSON.parse(r);
      const save = btns.find(b => b.text.includes('Save') || b.text.includes('Apply') || b.text.includes('Crop') || b.text.includes('Done'));
      if (save) {
        await clickAt(send, save.x, save.y);
        console.log(`Clicked: ${save.text}`);
        await sleep(3000);
      }
    }

    // Wait and recheck
    await sleep(2000);
    r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.includes('photo'))
        .map(el => el.textContent.trim().substring(0, 80));
      const imgs = Array.from(document.querySelectorAll('img'))
        .filter(el => el.getBoundingClientRect().width > 50 && !el.src.includes('svg'))
        .map(el => ({ src: el.src.substring(0, 80), w: Math.round(el.getBoundingClientRect().width) }));
      return JSON.stringify({ errors, imgs, body: document.body.innerText.substring(0, 200) });
    `);
    console.log("\nFinal photo status:", r);

    // Now try to review regardless
    await sleep(500);
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
        body: document.body.innerText.substring(0, 400)
      })`);
      const page = JSON.parse(r);
      console.log("\n=== Result:", page.step, "===");
      console.log(page.body.substring(0, 300));

      if (page.step !== 'location') {
        console.log("ADVANCED PAST LOCATION!");
        // Look for submit
        ws.close(); await sleep(1000);
        ({ ws, send, eval_ } = await connectToPage("upwork.com"));
        r = await eval_(`
          const btns = Array.from(document.querySelectorAll('button'))
            .filter(el => el.offsetParent !== null && !el.textContent.includes('Skip to'))
            .map(el => ({ text: el.textContent.trim().substring(0, 40), x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2), y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2) }));
          return JSON.stringify(btns);
        `);
        console.log("Buttons:", r);
        const btns = JSON.parse(r);
        const submit = btns.find(b => b.text.includes('Submit') || b.text.includes('Publish'));
        if (submit) {
          await clickAt(send, submit.x, submit.y);
          console.log(`Clicked: ${submit.text}`);
          await sleep(8000);
          ws.close(); await sleep(1000);
          ({ ws, send, eval_ } = await connectToPage("upwork.com"));
          r = await eval_(`return JSON.stringify({ url: location.href, body: document.body.innerText.substring(0, 500) })`);
          console.log("\n*** FINAL:", r);
        }
      }
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
