// Upload the pre-created image via CDP DOM.setFileInputFiles
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes("manage_gigs"));
  if (!tab) throw new Error("Gig page not found");
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
  await send("Input.dispatchMouseEvent", { type: "mousePressed", x, y, button: "left", clickCount: 1 });
  await sleep(80);
  await send("Input.dispatchMouseEvent", { type: "mouseReleased", x, y, button: "left", clickCount: 1 });
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Dismiss any old error messages
  await eval_(`
    const errorCloseButtons = Array.from(document.querySelectorAll('[class*="error"] button, [class*="error"] [class*="close"]'));
    errorCloseButtons.forEach(b => b.click());
  `);
  await sleep(500);

  // Get the DOM for the #image file input
  await send("DOM.enable", {});
  const doc = await send("DOM.getDocument", {});
  const imgInput = await send("DOM.querySelector", {
    nodeId: doc.root.nodeId,
    selector: "#image"
  });
  console.log("Image input nodeId:", imgInput.nodeId);

  if (imgInput.nodeId) {
    // Use the Windows path to the image file
    const filePath = "D:\\_CLAUDE-TOOLS\\fiverr-gig-proofreading.jpg";
    console.log(`Setting file: ${filePath}`);

    await send("DOM.setFileInputFiles", {
      files: [filePath],
      nodeId: imgInput.nodeId
    });
    console.log("File set via CDP");

    // Wait for upload processing
    console.log("Waiting for upload...");
    await sleep(10000);

    // Check status
    let r = await eval_(`
      const errors = Array.from(document.querySelectorAll('[class*="error"]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
        .map(el => el.textContent.trim().substring(0, 100));

      // Check for uploaded images/thumbnails
      const imgs = Array.from(document.querySelectorAll('img'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return el.offsetParent !== null && rect.y > 100 && rect.y < 800 && el.src;
        })
        .map(el => ({
          src: el.src.substring(0, 120),
          class: (el.className || '').substring(0, 40),
          w: Math.round(el.getBoundingClientRect().width),
          h: Math.round(el.getBoundingClientRect().height)
        }));

      // Check for upload success indicator
      const uploadArea = document.querySelector('[class*="gallery-image"]');
      const uploadText = uploadArea ? uploadArea.textContent.trim().substring(0, 200) : '';

      return JSON.stringify({ errors, imgs: imgs.slice(0, 5), uploadText });
    `);
    console.log("Upload status:", r);
    const status = JSON.parse(r);

    if (status.errors.length > 0) {
      console.log("Still has errors:", status.errors);
    }

    // Try Save & Continue regardless
    console.log("\n=== Saving ===");
    r = await eval_(`
      const btn = Array.from(document.querySelectorAll('button'))
        .find(b => b.textContent.trim() === 'Save & Continue');
      if (btn) {
        btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return 'found';
      }
      return 'not found';
    `);
    await sleep(800);

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
      await sleep(5000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          wizard: new URL(location.href).searchParams.get('wizard'),
          errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
            .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
            .map(el => el.textContent.trim().substring(0, 100)),
          body: (document.body?.innerText || '').substring(200, 800)
        });
      `);
      const result = JSON.parse(r);
      console.log(`\nResult: wizard=${result.wizard}`);
      console.log(`Errors: ${JSON.stringify(result.errors)}`);
      console.log(`Body: ${result.body.substring(0, 400)}`);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
