// Navigate to photo upload page and upload profile photo
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

  // Try navigating to the new-freelancer photo page
  console.log("Navigating to photo-and-name page...");
  await send("Page.navigate", { url: "https://www.freelancer.com/new-freelancer/profile-details/photo-and-name" });
  await sleep(5000);

  let r = await eval_(`return location.href`);
  console.log("URL:", r);

  // Check for file inputs and upload areas
  r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    const allInputs = Array.from(document.querySelectorAll('input'));
    const buttons = Array.from(document.querySelectorAll('button'))
      .filter(b => b.offsetParent !== null)
      .map(b => b.textContent.trim().substring(0, 40));

    // Look for avatar/photo upload area
    const uploadArea = document.querySelector('[class*="upload" i], [class*="avatar" i], [class*="photo" i], [class*="dropzone" i], [class*="drag" i]');

    return JSON.stringify({
      url: location.href,
      fileInputCount: fileInputs.length,
      fileInputDetails: fileInputs.map(f => ({
        id: f.id, name: f.name, accept: f.accept,
        class: f.className?.substring(0, 50),
        parentClass: f.parentElement?.className?.substring(0, 50),
        hidden: f.hidden || f.style.display === 'none',
        offsetParent: !!f.offsetParent
      })),
      totalInputs: allInputs.length,
      buttons,
      uploadArea: uploadArea ? {
        tag: uploadArea.tagName,
        class: uploadArea.className?.toString()?.substring(0, 60),
        text: uploadArea.textContent?.trim()?.substring(0, 60)
      } : null,
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nPage state:", r);

  const state = JSON.parse(r);

  if (state.fileInputCount > 0) {
    console.log("\n=== Found file input! Uploading photo... ===");

    await send("DOM.enable");
    await send("DOM.getDocument");

    // Try to get the file input node
    const evalResult = await send("Runtime.evaluate", {
      expression: `document.querySelector('input[type="file"]')`,
      returnByValue: false
    });

    if (evalResult.result?.objectId) {
      const nodeResult = await send("DOM.requestNode", {
        objectId: evalResult.result.objectId
      });
      console.log("Got node:", JSON.stringify(nodeResult));

      if (nodeResult.nodeId) {
        const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
        console.log(`Uploading: ${photoPath}`);
        await send("DOM.setFileInputFiles", {
          nodeId: nodeResult.nodeId,
          files: [photoPath]
        });
        console.log("File set!");
        await sleep(3000);

        // Check for preview/crop dialog
        r = await eval_(`
          const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="dialog" i], [class*="crop" i], [class*="overlay" i]'))
            .filter(el => el.offsetParent !== null || window.getComputedStyle(el).display !== 'none')
            .map(el => ({
              tag: el.tagName,
              class: el.className?.toString()?.substring(0, 60),
              text: el.textContent?.trim()?.substring(0, 100)
            }));
          const btns = Array.from(document.querySelectorAll('button'))
            .filter(b => b.offsetParent !== null)
            .map(b => ({
              text: b.textContent.trim().substring(0, 40),
              rect: (() => { const r = b.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2 }; })()
            }));
          return JSON.stringify({ modals, buttons: btns, preview: document.body.innerText.substring(0, 500) });
        `);
        console.log("\nAfter upload:", r);

        // Look for Save/Apply/Crop button
        const afterUpload = JSON.parse(r);
        const saveBtn = afterUpload.buttons.find(b =>
          b.text.toLowerCase().includes('save') ||
          b.text.toLowerCase().includes('apply') ||
          b.text.toLowerCase().includes('crop') ||
          b.text.toLowerCase().includes('done') ||
          b.text.toLowerCase().includes('upload')
        );

        if (saveBtn) {
          console.log(`\nClicking "${saveBtn.text}"...`);
          await send("Input.dispatchMouseEvent", { type: "mousePressed", x: saveBtn.rect.x, y: saveBtn.rect.y, button: "left", clickCount: 1 });
          await sleep(50);
          await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: saveBtn.rect.x, y: saveBtn.rect.y, button: "left", clickCount: 1 });
          await sleep(3000);
        }
      }
    }
  } else {
    console.log("\nNo file input found directly. Looking for clickable upload area...");

    // Try clicking on avatar/photo area to trigger file input
    r = await eval_(`
      const clickTargets = Array.from(document.querySelectorAll('*'))
        .filter(el => {
          const cls = el.className?.toString()?.toLowerCase() || '';
          const text = el.textContent?.trim()?.toLowerCase() || '';
          return el.offsetParent !== null && (
            cls.includes('avatar') || cls.includes('photo') || cls.includes('upload') ||
            cls.includes('picture') || cls.includes('dropzone') ||
            (text.includes('upload') && text.length < 100) ||
            (text.includes('drag') && text.length < 100) ||
            (text.includes('browse') && text.includes('photo') && text.length < 100)
          );
        })
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 60),
          text: el.textContent?.trim()?.substring(0, 60),
          rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height }; })()
        }));
      return JSON.stringify(clickTargets.slice(0, 8));
    `);
    console.log("Clickable upload areas:", r);

    const targets = JSON.parse(r);
    if (targets.length > 0) {
      // Click the most specific target (smallest area usually)
      const target = targets.find(t => t.rect.w > 0 && t.rect.h > 0 && t.rect.w < 500) || targets[0];
      console.log(`\nClicking "${target.text}" (${target.tag}.${target.class})...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: target.rect.x, y: target.rect.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: target.rect.x, y: target.rect.y, button: "left", clickCount: 1 });
      await sleep(2000);

      // Check if file input appeared
      r = await eval_(`
        const fi = Array.from(document.querySelectorAll('input[type="file"]'));
        return JSON.stringify({
          count: fi.length,
          details: fi.map(f => ({ id: f.id, name: f.name, accept: f.accept }))
        });
      `);
      console.log("File inputs after click:", r);

      const fiData = JSON.parse(r);
      if (fiData.count > 0) {
        await send("DOM.enable");
        await send("DOM.getDocument");

        const evalResult = await send("Runtime.evaluate", {
          expression: `document.querySelector('input[type="file"]')`,
          returnByValue: false
        });

        if (evalResult.result?.objectId) {
          const nodeResult = await send("DOM.requestNode", {
            objectId: evalResult.result.objectId
          });

          if (nodeResult.nodeId) {
            const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
            console.log(`Uploading: ${photoPath}`);
            await send("DOM.setFileInputFiles", {
              nodeId: nodeResult.nodeId,
              files: [photoPath]
            });
            console.log("File set!");
            await sleep(5000);

            // Check result
            r = await eval_(`
              const btns = Array.from(document.querySelectorAll('button'))
                .filter(b => b.offsetParent !== null)
                .map(b => ({ text: b.textContent.trim(), rect: (() => { const r = b.getBoundingClientRect(); return { x: r.x+r.width/2, y: r.y+r.height/2 }; })() }));
              return JSON.stringify({ buttons: btns, preview: document.body.innerText.substring(0, 500) });
            `);
            console.log("After upload:", r);
          }
        }
      }
    }
  }

  // Final state check
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 2000)
    });
  `);
  console.log("\n=== FINAL STATE ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
