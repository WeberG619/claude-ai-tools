// Upload gig image to the correct #image file input
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

  // Clear the previous error by dismissing it
  await eval_(`
    const closeBtn = document.querySelector('[class*="error"] [class*="close"], [class*="error"] button');
    if (closeBtn) closeBtn.click();
  `);
  await sleep(500);

  // Create canvas image and upload to the IMAGE file input specifically
  let r = await eval_(`
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 769;
    const ctx = canvas.getContext('2d');

    // Dark professional background
    const grad = ctx.createLinearGradient(0, 0, 1280, 769);
    grad.addColorStop(0, '#0a192f');
    grad.addColorStop(0.5, '#172a45');
    grad.addColorStop(1, '#1a365d');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 1280, 769);

    // Decorative accents
    ctx.fillStyle = '#e94560';
    ctx.fillRect(0, 0, 8, 769);
    ctx.fillRect(0, 0, 1280, 4);

    // Main title
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 64px Arial, Helvetica, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Professional', 640, 200);
    ctx.fillStyle = '#e94560';
    ctx.fillText('Proofreading & Editing', 640, 280);

    // Divider
    ctx.strokeStyle = '#e94560';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(440, 320);
    ctx.lineTo(840, 320);
    ctx.stroke();

    // Subtitle
    ctx.fillStyle = '#8892b0';
    ctx.font = '28px Arial, Helvetica, sans-serif';
    ctx.fillText('Grammar  •  Clarity  •  Style  •  Flow', 640, 370);

    // Features
    ctx.font = '22px Arial';
    ctx.fillStyle = '#ccd6f6';
    const features = [
      '✓ Grammar & Spelling Correction',
      '✓ Improved Sentence Structure',
      '✓ Track Changes Included',
      '✓ Fast 1-3 Day Delivery'
    ];
    features.forEach((f, i) => ctx.fillText(f, 640, 440 + i * 40));

    // Content types
    ctx.fillStyle = '#8892b0';
    ctx.font = '22px Arial';
    ctx.fillText('Articles  |  Books  |  Academic  |  Business  |  Web Content', 640, 620);

    // Bottom bar
    ctx.fillStyle = '#e94560';
    ctx.fillRect(0, 690, 1280, 79);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 30px Arial';
    ctx.fillText('Polished Writing, Every Time', 640, 740);

    return new Promise(resolve => {
      canvas.toBlob(blob => {
        if (!blob) { resolve('no blob'); return; }

        // Target the IMAGE file input specifically
        const imageInput = document.querySelector('#image');
        if (!imageInput) { resolve('no #image input'); return; }

        const file = new File([blob], 'proofreading-gig.jpg', { type: 'image/jpeg' });
        const dt = new DataTransfer();
        dt.items.add(file);
        imageInput.files = dt.files;
        imageInput.dispatchEvent(new Event('change', { bubbles: true }));
        imageInput.dispatchEvent(new Event('input', { bubbles: true }));
        resolve('uploaded to #image');
      }, 'image/jpeg', 0.92);
    });
  `);
  console.log("Upload result:", r);

  // Wait for processing
  console.log("Waiting for upload...");
  await sleep(8000);

  // Check upload status
  r = await eval_(`
    const thumbnails = Array.from(document.querySelectorAll('[class*="thumbnail"], [class*="preview"], [class*="gallery-image"], [class*="uploaded"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 80),
        src: el.src?.substring(0, 80) || '',
        bg: (el.style?.backgroundImage || '').substring(0, 80)
      }));

    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));

    const body = (document.body?.innerText || '').substring(0, 2000);
    return JSON.stringify({ thumbnails: thumbnails.slice(0, 10), errors, bodyHasImage: body.includes('proofreading-gig') });
  `);
  console.log("Status:", r);
  const status = JSON.parse(r);

  if (status.errors.length > 0) {
    console.log("Errors found:", status.errors);
    // If DataTransfer approach doesn't work, we need CDP setFileInputFiles
    console.log("\nTrying CDP DOM.setFileInputFiles approach...");

    // First get the DOM node for #image input
    const docResult = await send("DOM.getDocument", {});
    const rootNodeId = docResult.root.nodeId;

    const queryResult = await send("DOM.querySelector", {
      nodeId: rootNodeId,
      selector: "#image"
    });
    console.log("Image input nodeId:", queryResult.nodeId);

    if (queryResult.nodeId) {
      // We need to create a real file on disk first via a data URL download
      // Instead, let's try the Network.interceptFileChooser approach

      // Enable file chooser interception
      await send("Page.setInterceptFileChooserDialog", { enabled: true });
      console.log("File chooser interception enabled");

      // We can't use that without a real file path. Let's use a different approach.
      // Create a temporary file from the canvas data
      r = await eval_(`
        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 769;
        const ctx = canvas.getContext('2d');

        // Simple background
        ctx.fillStyle = '#172a45';
        ctx.fillRect(0, 0, 1280, 769);
        ctx.fillStyle = '#e94560';
        ctx.fillRect(0, 0, 1280, 4);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 64px Arial';
        ctx.textAlign = 'center';
        ctx.fillText('Professional', 640, 200);
        ctx.fillStyle = '#e94560';
        ctx.fillText('Proofreading & Editing', 640, 280);
        ctx.fillStyle = '#8892b0';
        ctx.font = '28px Arial';
        ctx.fillText('Grammar • Clarity • Style • Flow', 640, 370);
        ctx.fillStyle = '#ccd6f6';
        ctx.font = '22px Arial';
        ctx.fillText('✓ Grammar & Spelling  ✓ Sentence Structure  ✓ Track Changes', 640, 450);
        ctx.fillStyle = '#e94560';
        ctx.fillRect(0, 690, 1280, 79);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 30px Arial';
        ctx.fillText('Polished Writing, Every Time', 640, 740);

        return canvas.toDataURL('image/jpeg', 0.92);
      `);

      // Save the data URL to a temp file via fetch and blob
      // Actually, let's write it to disk using the CDP
      const base64Data = r.split(',')[1];

      // Write to temp file using node fs (we're in the node process)
      const fs = await import('fs');
      const path = await import('path');
      const tmpFile = 'C:\\Users\\happ\\AppData\\Local\\Temp\\fiverr-gig-image.jpg';
      fs.writeFileSync(tmpFile, Buffer.from(base64Data, 'base64'));
      console.log(`Saved image to ${tmpFile} (${fs.statSync(tmpFile).size} bytes)`);

      // Now use DOM.setFileInputFiles to set the file
      await send("DOM.setFileInputFiles", {
        files: [tmpFile],
        nodeId: queryResult.nodeId
      });
      console.log("Set file via CDP");

      await sleep(8000);

      // Check again
      r = await eval_(`
        const errors = Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100));
        const imgs = Array.from(document.querySelectorAll('img'))
          .filter(el => el.offsetParent !== null && el.getBoundingClientRect().y > 100 && el.getBoundingClientRect().y < 800)
          .map(el => ({ src: el.src?.substring(0, 100), class: (el.className || '').substring(0, 40) }));
        return JSON.stringify({ errors, imgs });
      `);
      console.log("After CDP upload:", r);
    }
  }

  // Try Save & Continue
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
        body: (document.body?.innerText || '').substring(200, 600)
      });
    `);
    const result = JSON.parse(r);
    console.log(`\nResult: wizard=${result.wizard}`);
    console.log(`Errors: ${JSON.stringify(result.errors)}`);
    console.log(`Body: ${result.body.substring(0, 300)}`);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
