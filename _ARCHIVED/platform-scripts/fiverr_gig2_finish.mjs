// Push through Requirements → Gallery → Publish
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

async function clickSaveAndContinue(send, eval_) {
  let r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Save & Continue');
    if (btn) {
      btn.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return 'found';
    }
    return 'not found';
  `);
  if (r === 'not found') return false;
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
  const btn = JSON.parse(r);
  if (!btn.error) {
    console.log(`  Clicking Save at (${btn.x}, ${btn.y})`);
    await clickAt(send, btn.x, btn.y);
    await sleep(5000);

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100))
      });
    `);
    const result = JSON.parse(r);
    console.log(`  Result: wizard=${result.wizard}, errors=${JSON.stringify(result.errors)}`);
    return true;
  }
  return false;
}

async function main() {
  const { ws, send, eval_ } = await connectToPage();
  console.log("Connected\n");

  // Check current state
  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 800)
    });
  `);
  const state = JSON.parse(r);
  console.log(`Current wizard: ${state.wizard}`);
  console.log(`Body: ${state.body.substring(0, 300)}`);

  // Step 3: Requirements - just save (optional questions are pre-filled by Fiverr)
  if (state.wizard === '3') {
    console.log("\n=== Requirements (wizard=3) ===");
    await clickSaveAndContinue(send, eval_);
  }

  // Check if we're on Gallery now
  r = await eval_(`
    return JSON.stringify({
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 1000)
    });
  `);
  let current = JSON.parse(r);
  console.log(`\nCurrent wizard: ${current.wizard}`);

  // Step 4: Gallery
  if (current.wizard === '4') {
    console.log("\n=== Gallery (wizard=4) ===");
    console.log("Body:", current.body.substring(0, 400));

    // Gallery requires at least 1 image. Let's check if there's an upload area
    r = await eval_(`
      const uploads = Array.from(document.querySelectorAll('input[type="file"], [class*="upload"], [class*="dropzone"]'))
        .filter(el => el.offsetParent !== null || el.type === 'file')
        .map(el => ({
          tag: el.tagName,
          type: el.type || '',
          accept: el.accept || '',
          class: (el.className?.toString() || '').substring(0, 60),
          y: Math.round(el.getBoundingClientRect().y)
        }));
      return JSON.stringify(uploads);
    `);
    console.log("Upload elements:", r);

    // Try to save without image first
    await clickSaveAndContinue(send, eval_);

    // Check if it advanced or has errors
    r = await eval_(`
      return JSON.stringify({
        wizard: new URL(location.href).searchParams.get('wizard'),
        errors: Array.from(document.querySelectorAll('[class*="error"], [role="alert"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
          .map(el => el.textContent.trim().substring(0, 100))
      });
    `);
    const galleryResult = JSON.parse(r);
    console.log(`After gallery save: wizard=${galleryResult.wizard}, errors=${JSON.stringify(galleryResult.errors)}`);

    if (galleryResult.wizard === '4' && galleryResult.errors.length > 0) {
      console.log("\nGallery requires an image. Creating a simple gig image...");

      // Create a simple gig image using canvas and upload it
      r = await eval_(`
        // Create a canvas-based gig image
        const canvas = document.createElement('canvas');
        canvas.width = 1280;
        canvas.height = 769;
        const ctx = canvas.getContext('2d');

        // Background gradient
        const grad = ctx.createLinearGradient(0, 0, 1280, 769);
        grad.addColorStop(0, '#1a1a2e');
        grad.addColorStop(0.5, '#16213e');
        grad.addColorStop(1, '#0f3460');
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, 1280, 769);

        // Title text
        ctx.fillStyle = '#e94560';
        ctx.font = 'bold 56px Arial, sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Professional', 640, 250);
        ctx.fillText('Proofreading & Editing', 640, 320);

        // Subtitle
        ctx.fillStyle = '#ffffff';
        ctx.font = '32px Arial, sans-serif';
        ctx.fillText('Grammar | Clarity | Style | Flow', 640, 400);

        // Features
        ctx.font = '24px Arial, sans-serif';
        ctx.fillStyle = '#a0d2db';
        const features = [
          '✓ Thorough grammar & spelling correction',
          '✓ Improved sentence structure',
          '✓ Track changes included',
          '✓ Fast turnaround'
        ];
        features.forEach((f, i) => {
          ctx.fillText(f, 640, 480 + i * 40);
        });

        // Bottom bar
        ctx.fillStyle = '#e94560';
        ctx.fillRect(0, 700, 1280, 69);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 28px Arial, sans-serif';
        ctx.fillText('Articles | Books | Academic | Business | Web Content', 640, 740);

        // Convert to blob and create File
        return new Promise(resolve => {
          canvas.toBlob(blob => {
            if (blob) {
              // Find the file input
              const fileInput = document.querySelector('input[type="file"]');
              if (fileInput) {
                const file = new File([blob], 'gig-proofreading.png', { type: 'image/png' });
                const dt = new DataTransfer();
                dt.items.add(file);
                fileInput.files = dt.files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
                resolve('uploaded');
              } else {
                resolve('no file input');
              }
            } else {
              resolve('no blob');
            }
          }, 'image/png');
        });
      `);
      console.log("Canvas upload:", r);
      await sleep(5000);

      // Check if upload was accepted
      r = await eval_(`
        const uploaded = Array.from(document.querySelectorAll('[class*="uploaded"], [class*="preview"], [class*="thumbnail"], img'))
          .filter(el => {
            const rect = el.getBoundingClientRect();
            return el.offsetParent !== null && rect.y > 100 && rect.y < 800;
          })
          .map(el => ({
            tag: el.tagName,
            class: (el.className?.toString() || '').substring(0, 60),
            src: el.src?.substring(0, 80) || ''
          }));
        return JSON.stringify(uploaded);
      `);
      console.log("After upload:", r);

      // Try save again
      await sleep(2000);
      await clickSaveAndContinue(send, eval_);
    }
  }

  // Check final state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      wizard: new URL(location.href).searchParams.get('wizard'),
      body: (document.body?.innerText || '').substring(200, 1000)
    });
  `);
  current = JSON.parse(r);
  console.log(`\nFinal wizard: ${current.wizard}`);
  console.log(`Body: ${current.body.substring(0, 500)}`);

  // Step 5: Publish
  if (current.wizard === '5') {
    console.log("\n=== Publish (wizard=5) ===");

    r = await eval_(`
      const publishBtn = Array.from(document.querySelectorAll('button, a'))
        .find(el => {
          const text = el.textContent.trim();
          return (text.includes('Publish') || text === 'Publish Gig') && el.offsetParent !== null;
        });
      if (publishBtn) {
        publishBtn.scrollIntoView({ block: 'center' });
        const rect = publishBtn.getBoundingClientRect();
        return JSON.stringify({
          text: publishBtn.textContent.trim().substring(0, 30),
          x: Math.round(rect.x + rect.width/2),
          y: Math.round(rect.y + rect.height/2)
        });
      }
      return JSON.stringify({ error: 'no publish button' });
    `);
    console.log("Publish button:", r);
    const pubBtn = JSON.parse(r);

    if (!pubBtn.error) {
      await sleep(500);
      console.log(`Clicking Publish at (${pubBtn.x}, ${pubBtn.y})`);
      await clickAt(send, pubBtn.x, pubBtn.y);
      await sleep(8000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          body: (document.body?.innerText || '').substring(0, 500)
        });
      `);
      console.log("After publish:", r);
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
