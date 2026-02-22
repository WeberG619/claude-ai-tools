// Upload profile photo to PPH via CDP file chooser
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
const fs = await import('fs');
const path = await import('path');

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
  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";

  // Check photo exists
  try {
    const winPath = photoPath.replace(/\\/g, '/');
    const wslPath = '/mnt/d/007 - DOCUMENTS TO BE FILED/Weber Files/Weber\'s Photo.jpg';
    const stats = fs.statSync(wslPath);
    console.log(`Photo found: ${stats.size} bytes`);
  } catch (e) {
    console.error("Photo not found at expected path, checking...");
    // Try alternate paths
    const altPaths = [
      '/mnt/d/007 - DOCUMENTS TO BE FILED/Weber Files/',
    ];
    for (const dir of altPaths) {
      try {
        const files = fs.readdirSync(dir).filter(f => f.toLowerCase().includes('photo') || f.toLowerCase().includes('weber'));
        console.log(`Files in ${dir}:`, files);
      } catch(e2) {
        console.log(`Cannot read ${dir}: ${e2.message}`);
      }
    }
  }

  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected\n");

  // Enable DOM and File chooser interception
  await send("DOM.enable");
  await send("Page.enable");

  // Find the file input element
  let r = await eval_(`
    const fileInputs = Array.from(document.querySelectorAll('input[type="file"]'));
    return JSON.stringify(fileInputs.map(f => ({
      id: f.id, name: f.name, accept: f.accept, multiple: f.multiple,
      class: (f.className || '').substring(0, 80),
      parentClass: (f.parentElement?.className || '').substring(0, 80)
    })));
  `);
  console.log("File inputs:", r);

  const fileInputs = JSON.parse(r);

  if (fileInputs.length > 0) {
    const input = fileInputs[0];
    console.log(`Using file input: id="${input.id}"`);

    // Method 1: Use DOM.setFileInputFiles via CDP
    // First get the node ID
    const docResult = await send("DOM.getDocument");
    const rootNodeId = docResult.root.nodeId;

    // Find the file input node
    const searchResult = await send("DOM.querySelectorAll", {
      nodeId: rootNodeId,
      selector: 'input[type="file"]'
    });

    if (searchResult.nodeIds && searchResult.nodeIds.length > 0) {
      const fileNodeId = searchResult.nodeIds[0];
      console.log(`File input node ID: ${fileNodeId}`);

      // Set the file
      try {
        await send("DOM.setFileInputFiles", {
          nodeId: fileNodeId,
          files: [photoPath]
        });
        console.log("File set via DOM.setFileInputFiles!");
        await sleep(3000);

        // Check if upload happened
        r = await eval_(`
          return JSON.stringify({
            hasUploadedFile: document.querySelectorAll('.plupload_file_name, [class*="file-name"], [class*="preview"]').length,
            error: document.querySelector('[class*="upload-error"], [class*="error"]')?.textContent?.trim()?.substring(0, 100) || '',
            uploadArea: document.querySelector('.plupload, [class*="upload"]')?.textContent?.trim()?.substring(0, 200) || '',
            profilePic: !!document.querySelector('.profile-photo img, [class*="profile"] img')
          });
        `);
        console.log("After upload:", r);
      } catch (e) {
        console.log("DOM.setFileInputFiles failed:", e.message);

        // Method 2: Try using Page.fileChooserIntercepted
        console.log("\nTrying Method 2: File chooser interception...");
        try {
          await send("Page.setInterceptFileChooserDialog", { enabled: true });

          // Set up listener for file chooser
          const fileChooserPromise = new Promise((resolve) => {
            const origHandler = ws.onmessage;
            const handler = (event) => {
              const msg = JSON.parse(event.data);
              if (msg.method === "Page.fileChooserOpened") {
                resolve(msg.params);
              }
            };
            ws.addEventListener("message", handler);
            // Timeout after 5 seconds
            setTimeout(() => { ws.removeEventListener("message", handler); resolve(null); }, 5000);
          });

          // Click the browse button or the upload area
          await eval_(`
            const browseBtn = document.querySelector('.plupload_button, [class*="browse"], a[id*="browse"]');
            if (browseBtn) { browseBtn.click(); return 'clicked browse'; }
            const uploadArea = document.querySelector('.plupload, [class*="dropzone"]');
            if (uploadArea) { uploadArea.click(); return 'clicked upload area'; }
            return 'no button found';
          `);

          const chooserEvent = await fileChooserPromise;
          if (chooserEvent) {
            console.log("File chooser opened, handling...");
            await send("Page.handleFileChooser", {
              action: "accept",
              files: [photoPath]
            });
            console.log("File accepted!");
            await sleep(3000);
          } else {
            console.log("File chooser did not open");
          }
        } catch (e2) {
          console.log("Method 2 failed:", e2.message);
        }
      }
    }
  }

  // Check final state
  console.log("\n=== POST-UPLOAD STATE ===");
  r = await eval_(`
    const errorEl = document.querySelector('[class*="error"]');
    const photoError = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('upload at least') && el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 100));

    return JSON.stringify({
      photoError,
      uploadArea: document.querySelector('.plupload, [class*="upload"], [class*="drop"]')?.innerHTML?.substring(0, 300) || '',
      allErrors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3)
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
