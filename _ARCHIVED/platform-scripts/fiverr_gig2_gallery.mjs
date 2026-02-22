// Upload a canvas-generated gig image for Gallery step
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

  // Find the file input for image upload
  let r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'))
      .map(el => ({
        accept: el.accept,
        name: el.name,
        id: el.id,
        class: (el.className?.toString() || '').substring(0, 60),
        multiple: el.multiple
      }));
    return JSON.stringify(fileInputs);
  `);
  console.log("File inputs:", r);

  // Create canvas image and upload via file input
  r = await eval_(`
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

    // Decorative left bar
    ctx.fillStyle = '#e94560';
    ctx.fillRect(0, 0, 8, 769);

    // Top accent line
    const accentGrad = ctx.createLinearGradient(0, 0, 1280, 0);
    accentGrad.addColorStop(0, '#e94560');
    accentGrad.addColorStop(1, '#ff6b6b');
    ctx.fillStyle = accentGrad;
    ctx.fillRect(0, 0, 1280, 4);

    // Main title
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 64px Arial, Helvetica, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('Professional', 640, 200);

    ctx.fillStyle = '#e94560';
    ctx.font = 'bold 64px Arial, Helvetica, sans-serif';
    ctx.fillText('Proofreading & Editing', 640, 280);

    // Divider line
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

    // Feature boxes
    const features = [
      { icon: '✓', text: 'Grammar & Spelling' },
      { icon: '✓', text: 'Sentence Structure' },
      { icon: '✓', text: 'Track Changes' },
      { icon: '✓', text: 'Fast Delivery' }
    ];

    ctx.font = '24px Arial, Helvetica, sans-serif';
    const startX = 240;
    const boxWidth = 200;
    const boxSpacing = 270;
    features.forEach((f, i) => {
      const x = startX + i * boxSpacing;
      const y = 420;

      // Box background
      ctx.fillStyle = 'rgba(233, 69, 96, 0.1)';
      ctx.fillRect(x - 80, y, boxWidth, 60);
      ctx.strokeStyle = 'rgba(233, 69, 96, 0.3)';
      ctx.strokeRect(x - 80, y, boxWidth, 60);

      // Text
      ctx.fillStyle = '#64ffda';
      ctx.textAlign = 'center';
      ctx.font = 'bold 22px Arial';
      ctx.fillText(f.icon, x + 20, y + 35);
      ctx.fillStyle = '#ccd6f6';
      ctx.font = '18px Arial';
      ctx.fillText(f.text, x + 20, y + 52);
    });

    // Content types
    ctx.textAlign = 'center';
    ctx.fillStyle = '#8892b0';
    ctx.font = '22px Arial';
    ctx.fillText('Articles  |  Books  |  Academic  |  Business  |  Web Content', 640, 550);

    // Bottom bar
    ctx.fillStyle = '#e94560';
    ctx.fillRect(0, 690, 1280, 79);
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 30px Arial';
    ctx.fillText('Polished Writing, Every Time', 640, 740);

    return new Promise(resolve => {
      canvas.toBlob(blob => {
        if (!blob) { resolve('no blob'); return; }

        const fileInputs = document.querySelectorAll('input[type="file"]');
        let targetInput = null;
        for (const inp of fileInputs) {
          if (inp.accept && (inp.accept.includes('image') || inp.accept.includes('png') || inp.accept.includes('jpeg'))) {
            targetInput = inp;
            break;
          }
        }
        if (!targetInput && fileInputs.length > 0) targetInput = fileInputs[0];

        if (targetInput) {
          const file = new File([blob], 'proofreading-gig.png', { type: 'image/png' });
          const dt = new DataTransfer();
          dt.items.add(file);
          targetInput.files = dt.files;
          targetInput.dispatchEvent(new Event('change', { bubbles: true }));
          targetInput.dispatchEvent(new Event('input', { bubbles: true }));
          resolve('uploaded to: ' + (targetInput.accept || 'no-accept'));
        } else {
          resolve('no suitable file input');
        }
      }, 'image/png');
    });
  `);
  console.log("Upload result:", r);

  // Wait for upload to process
  console.log("Waiting for upload processing...");
  await sleep(8000);

  // Check upload status
  r = await eval_(`
    // Look for upload progress, thumbnails, or success indicators
    const thumbnails = Array.from(document.querySelectorAll('img, [class*="thumbnail"], [class*="preview"], [class*="upload"]'))
      .filter(el => {
        const rect = el.getBoundingClientRect();
        return el.offsetParent !== null && rect.y > 100 && rect.y < 800 &&
               (el.src || el.style?.backgroundImage || el.className?.includes('upload'));
      })
      .map(el => ({
        tag: el.tagName,
        class: (el.className?.toString() || '').substring(0, 60),
        src: (el.src || '').substring(0, 80),
        bg: (el.style?.backgroundImage || '').substring(0, 80)
      }));

    const progress = Array.from(document.querySelectorAll('[class*="progress"], [class*="loading"], [class*="uploading"]'))
      .filter(el => el.offsetParent !== null)
      .map(el => ({
        class: (el.className?.toString() || '').substring(0, 60),
        text: el.textContent.trim().substring(0, 40)
      }));

    const errors = Array.from(document.querySelectorAll('[class*="error"]'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 200)
      .map(el => el.textContent.trim().substring(0, 100));

    return JSON.stringify({ thumbnails: thumbnails.slice(0, 5), progress, errors });
  `);
  console.log("Upload status:", r);

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
        body: (document.body?.innerText || '').substring(200, 800)
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
