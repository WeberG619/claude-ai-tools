// Gallery upload - target portfolio section file input
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
  let { ws, send, eval_ } = await connectToPage("manage_gigs");
  console.log("Connected\n");

  await send("DOM.enable");

  // Diagnose: list ALL file inputs and ALL gallery items
  let r = await eval_(`
    const allFileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(allFileInputs.map((el, i) => ({
      idx: i,
      id: el.id,
      name: el.name,
      accept: el.accept,
      parentSection: el.closest('.gallery-section')?.className || 'no-section',
      visible: el.offsetParent !== null
    })));
  `);
  console.log("All file inputs:", r);

  // Check portfolio section specifically
  r = await eval_(`
    const portfolio = document.querySelector('.portfolio-section');
    if (!portfolio) return 'no portfolio section';
    const items = Array.from(portfolio.querySelectorAll('.gallery-item-placeholder'));
    const inputs = Array.from(portfolio.querySelectorAll('input'));
    const links = Array.from(portfolio.querySelectorAll('a, [class*="browse"], [class*="upload"]'));
    return JSON.stringify({
      html: portfolio.innerHTML.substring(0, 500),
      items: items.length,
      inputs: inputs.map(el => ({ id: el.id, type: el.type, name: el.name })),
      links: links.map(el => ({ tag: el.tagName, text: el.textContent.trim().substring(0, 30), class: (el.className || '').substring(0, 40) }))
    });
  `);
  console.log("\nPortfolio section:", r);

  // Get document root
  const docResult = await send("DOM.getDocument", { depth: 0 });
  const rootNodeId = docResult.root.nodeId;

  // Try all approaches for uploading
  console.log("\n=== Upload attempts ===");

  // Approach 1: Try re-upload-file-0
  try {
    const node1 = await send("DOM.querySelector", { nodeId: rootNodeId, selector: '#re-upload-file-0' });
    if (node1.nodeId > 0) {
      console.log("Found #re-upload-file-0, nodeId:", node1.nodeId);
      await send("DOM.setFileInputFiles", { nodeId: node1.nodeId, files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"] });
      console.log("File set on #re-upload-file-0");
      await sleep(5000);
      r = await eval_(`
        const portfolio = document.querySelector('.portfolio-section');
        const imgs = portfolio ? Array.from(portfolio.querySelectorAll('img')).map(el => el.src.substring(0, 80)) : [];
        const errors = Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
          .map(el => el.textContent.trim().substring(0, 100));
        return JSON.stringify({ imgs, errors });
      `);
      console.log("After re-upload-file-0:", r);
    }
  } catch(e) { console.log("re-upload-file-0 error:", e.message); }

  // Approach 2: Try portfolio section's first visible input
  try {
    const node2 = await send("DOM.querySelector", { nodeId: rootNodeId, selector: '.portfolio-section input[type="file"]' });
    if (node2.nodeId > 0) {
      console.log("\nFound portfolio file input, nodeId:", node2.nodeId);
      await send("DOM.setFileInputFiles", { nodeId: node2.nodeId, files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"] });
      console.log("File set on portfolio input");
      await sleep(5000);
      r = await eval_(`
        const portfolio = document.querySelector('.portfolio-section');
        const imgs = portfolio ? Array.from(portfolio.querySelectorAll('img')).map(el => el.src.substring(0, 80)) : [];
        const items = portfolio ? Array.from(portfolio.querySelectorAll('.gallery-item-placeholder')).map(el => ({
          class: el.className.substring(0, 60),
          hasImg: !!el.querySelector('img'),
          style: el.querySelector('img')?.style?.cssText?.substring(0, 80) || '',
          bg: el.style?.backgroundImage?.substring(0, 80) || ''
        })) : [];
        return JSON.stringify({ imgs, items });
      `);
      console.log("After portfolio input:", r);
    }
  } catch(e) { console.log("portfolio input error:", e.message); }

  // Approach 3: Try the #image input and trigger change event via JS
  try {
    const node3 = await send("DOM.querySelector", { nodeId: rootNodeId, selector: '#image' });
    if (node3.nodeId > 0) {
      console.log("\nFound #image, nodeId:", node3.nodeId);
      await send("DOM.setFileInputFiles", { nodeId: node3.nodeId, files: ["D:\\_CLAUDE-TOOLS\\fiverr_gig3_image.png"] });
      // Also dispatch change event
      await eval_(`
        const imageInput = document.getElementById('image');
        if (imageInput) {
          imageInput.dispatchEvent(new Event('change', { bubbles: true }));
          imageInput.dispatchEvent(new Event('input', { bubbles: true }));
        }
        return 'dispatched';
      `);
      console.log("File set on #image with change event");
      await sleep(5000);
      r = await eval_(`
        const imgs = Array.from(document.querySelectorAll('.portfolio-section img, .gallery-item img')).map(el => el.src.substring(0, 80));
        const errors = Array.from(document.querySelectorAll('[class*="error"]'))
          .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
          .map(el => el.textContent.trim().substring(0, 100));
        return JSON.stringify({ imgs, errors });
      `);
      console.log("After #image with event:", r);
    }
  } catch(e) { console.log("#image error:", e.message); }

  // Check final state
  console.log("\n=== Final state ===");
  r = await eval_(`
    const body = document.body.innerText;
    const galleryPart = body.substring(body.indexOf('Gig Image'), body.indexOf('Gig Image') + 500);
    return galleryPart || body.substring(0, 500);
  `);
  console.log("Page text around images:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
