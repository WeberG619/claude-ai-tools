// Upload profile photo to Freelancer via CDP DOM.setFileInputFiles
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) throw new Error(`Page not found: ${urlMatch}`);
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

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // Find file input for profile picture
  let r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(fileInputs.map(f => ({
      id: f.id,
      name: f.name,
      accept: f.accept,
      class: f.className?.substring(0, 50),
      hidden: f.style.display === 'none' || !f.offsetParent
    })));
  `);
  console.log("File inputs found:", r);

  const fileInputs = JSON.parse(r);

  if (fileInputs.length === 0) {
    console.log("No file input found! Checking for upload buttons...");
    r = await eval_(`
      const uploadBtns = Array.from(document.querySelectorAll('*'))
        .filter(el => el.offsetParent !== null && (
          el.textContent.trim().toLowerCase().includes('upload') ||
          el.textContent.trim().toLowerCase().includes('photo') ||
          el.textContent.trim().toLowerCase().includes('picture') ||
          el.className?.toString()?.toLowerCase()?.includes('avatar') ||
          el.className?.toString()?.toLowerCase()?.includes('photo')
        ))
        .map(el => ({ tag: el.tagName, text: el.textContent.trim().substring(0, 50), class: el.className?.toString()?.substring(0, 50) }));
      return JSON.stringify(uploadBtns.slice(0, 10));
    `);
    console.log("Upload elements:", r);
    ws.close();
    return;
  }

  // Use DOM.setFileInputFiles to set the file on the input
  // First, get the nodeId of the file input
  console.log("\nEnabling DOM...");
  await send("DOM.enable");
  await send("DOM.getDocument");

  // Find the file input node
  const fileInput = fileInputs[0]; // Use the first file input
  const selector = fileInput.id ? `#${fileInput.id}` : 'input[type="file"]';

  // Get the node using querySelector
  r = await send("DOM.querySelector", {
    nodeId: 1, // document node
    selector: selector
  });

  if (!r.nodeId && r.nodeId !== 0) {
    // Try alternative: use Runtime to get the element and then use DOM.resolveNode
    console.log("querySelector failed, trying Runtime approach...");

    const evalResult = await send("Runtime.evaluate", {
      expression: `document.querySelector('input[type="file"]')`,
      returnByValue: false
    });

    if (evalResult.result?.objectId) {
      const nodeResult = await send("DOM.requestNode", {
        objectId: evalResult.result.objectId
      });
      console.log("Got node:", nodeResult);

      if (nodeResult.nodeId) {
        // Windows path for the photo
        const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

        console.log(`\nUploading photo: ${photoPath}`);
        await send("DOM.setFileInputFiles", {
          nodeId: nodeResult.nodeId,
          files: [photoPath]
        });
        console.log("File set on input!");
        await sleep(3000);
      }
    }
  } else {
    const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
    console.log(`\nUploading photo: ${photoPath}`);
    await send("DOM.setFileInputFiles", {
      nodeId: r.nodeId,
      files: [photoPath]
    });
    console.log("File set on input!");
    await sleep(3000);
  }

  // Check if photo was uploaded
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 100));
    const hasPhotoError = errors.some(e => e.toLowerCase().includes('photo') || e.toLowerCase().includes('picture'));
    const avatarImg = document.querySelector('[class*="avatar"] img, [class*="photo"] img, [class*="profile"] img');
    return JSON.stringify({
      errors,
      hasPhotoError,
      avatarSrc: avatarImg?.src?.substring(0, 80) || 'none',
      preview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("\nAfter upload:", r);

  // Now try to save again
  console.log("\nSaving profile again...");
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save' && b.offsetParent !== null);
    if (btn) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    console.log("Clicked Save");
  }
  await sleep(5000);

  // Check final result
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('[class*="error"], [class*="Error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
      .map(el => el.textContent.trim().substring(0, 100));
    const hasBid = document.body.innerText.includes('Place a Bid') || document.body.innerText.includes('Bid Amount');
    const stillNeeds = document.body.innerText.includes('Complete your profile');
    return JSON.stringify({ errors: [...new Set(errors)], hasBid, stillNeeds });
  `);
  console.log("\n=== FINAL ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
