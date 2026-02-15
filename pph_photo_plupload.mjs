// Upload photo via Plupload API on PPH
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
  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected\n");

  // Enable required domains
  await send("DOM.enable");
  await send("Page.enable");

  // Investigate Plupload setup
  console.log("=== Investigating Plupload ===");
  let r = await eval_(`
    // Check for Plupload instances
    const pluploadExists = typeof plupload !== 'undefined';
    const moxieExists = typeof moxie !== 'undefined';

    // Find uploader instances - they're usually stored in global or jQuery data
    let uploaderInfo = null;

    // Check for global uploader
    if (window.uploader) {
      uploaderInfo = { source: 'window.uploader', id: window.uploader.id, state: window.uploader.state, files: window.uploader.files?.length };
    }

    // Check jQuery data on upload elements
    const $ = jQuery;
    let jqUploader = null;
    try {
      const uploadEl = $('[class*="plupload"], [class*="upload"]').first();
      if (uploadEl.length) {
        const data = uploadEl.data();
        jqUploader = { dataKeys: Object.keys(data), element: uploadEl[0].className.substring(0, 80) };
      }
    } catch(e) {}

    // Check for uploader in the browse button container
    const browseBtn = document.querySelector('[id*="browse"], .moxie-shim');
    const browseBtnInfo = browseBtn ? {
      id: browseBtn.id, class: browseBtn.className.substring(0, 80),
      parentId: browseBtn.parentElement?.id,
      parentClass: browseBtn.parentElement?.className?.substring(0, 80)
    } : null;

    // Try to find uploader via plupload runtime IDs
    let runtimeUploaders = [];
    if (pluploadExists) {
      // Plupload stores uploaders internally
      try {
        runtimeUploaders = Object.keys(plupload.cache || {});
      } catch(e) {}
    }

    return JSON.stringify({
      pluploadExists, moxieExists, uploaderInfo, jqUploader,
      browseBtnInfo, runtimeUploaders
    });
  `);
  console.log(r);

  // Try to find the Plupload uploader instance
  console.log("\n=== Finding uploader instance ===");
  r = await eval_(`
    // Search for uploader by looking at all global variables
    const uploaderKeys = [];
    for (const key in window) {
      try {
        const val = window[key];
        if (val && typeof val === 'object' && val.start && val.addFile && val.settings) {
          uploaderKeys.push(key);
        }
      } catch(e) {}
    }

    // Also check if there's an uploader attached to specific elements
    const allElements = document.querySelectorAll('[id]');
    const uploadRelated = Array.from(allElements)
      .filter(el => el.id.includes('upload') || el.id.includes('plupload') || el.id.includes('html5'))
      .map(el => ({ id: el.id, tag: el.tagName, class: (el.className || '').substring(0, 60) }));

    // Check the profile picture section HTML
    const picSection = document.querySelector('.profile-picture, [class*="profile-picture"], [class*="ProfilePicture"]');
    const sectionHtml = picSection?.outerHTML?.substring(0, 500) || 'not found';

    // Look at scripts for uploader initialization
    const scripts = Array.from(document.querySelectorAll('script'))
      .map(s => s.textContent)
      .filter(t => t.includes('plupload') || t.includes('Uploader'))
      .map(t => t.substring(0, 300));

    return JSON.stringify({
      uploaderKeys,
      uploadRelated,
      sectionHtml,
      inlineScripts: scripts.length
    });
  `);
  console.log(r);

  // Try using file chooser interception approach
  console.log("\n=== Trying File Chooser Interception ===");

  // Enable file chooser interception
  await send("Page.setInterceptFileChooserDialog", { enabled: true });

  // Set up a listener for the file chooser event
  let fileChooserResolve;
  const fileChooserPromise = new Promise((resolve) => {
    fileChooserResolve = resolve;
    setTimeout(() => resolve(null), 8000);
  });

  const origOnMessage = ws.onmessage;
  ws.addEventListener("message", function handler(event) {
    const msg = JSON.parse(event.data);
    if (msg.method === "Page.fileChooserOpened") {
      console.log("File chooser opened!", JSON.stringify(msg.params));
      fileChooserResolve(msg.params);
      ws.removeEventListener("message", handler);
    }
  });

  // Click the browse/upload button area
  r = await eval_(`
    // Find all clickable elements in the photo upload area
    const photoSection = document.querySelector('.profile-picture-uploader, [class*="profile-picture"]');

    // Look for "browse" text link
    const browseLink = Array.from(document.querySelectorAll('a, span, div'))
      .find(el => el.textContent.trim() === 'browse' && el.offsetParent !== null);

    if (browseLink) {
      browseLink.click();
      return 'clicked browse link: ' + browseLink.tagName + '.' + (browseLink.className || '').substring(0, 40);
    }

    // Click the drop zone area
    const dropZone = document.querySelector('.plupload, [class*="dropzone"], [class*="drop-zone"]');
    if (dropZone) {
      dropZone.click();
      return 'clicked drop zone';
    }

    // Click the moxie shim (Plupload's hidden file input trigger)
    const shim = document.querySelector('.moxie-shim');
    if (shim) {
      shim.click();
      return 'clicked moxie shim';
    }

    return 'no clickable upload element found';
  `);
  console.log("Click result:", r);

  const chooserEvent = await fileChooserPromise;

  if (chooserEvent) {
    console.log("Handling file chooser...");
    try {
      await send("Page.handleFileChooser", {
        action: "accept",
        files: [photoPath]
      });
      console.log("File accepted via file chooser!");
      await sleep(5000);
    } catch (e) {
      console.log("handleFileChooser error:", e.message);
    }
  } else {
    console.log("File chooser did not open via click, trying direct file input approach...");

    // Try clicking the actual file input directly
    r = await eval_(`
      const fileInput = document.querySelector('input[type="file"]');
      if (fileInput) {
        // Make it visible first
        fileInput.style.opacity = '1';
        fileInput.style.position = 'relative';
        fileInput.style.zIndex = '99999';
        fileInput.style.width = '200px';
        fileInput.style.height = '50px';
        const rect = fileInput.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
      }
      return null;
    `);

    if (r) {
      const pos = JSON.parse(r);
      console.log(`Clicking file input at (${pos.x}, ${pos.y})`);

      // Wait a bit for the listener
      await sleep(500);

      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });

      const chooserEvent2 = await new Promise((resolve) => {
        const handler = (event) => {
          const msg = JSON.parse(event.data);
          if (msg.method === "Page.fileChooserOpened") {
            resolve(msg.params);
            ws.removeEventListener("message", handler);
          }
        };
        ws.addEventListener("message", handler);
        setTimeout(() => { ws.removeEventListener("message", handler); resolve(null); }, 5000);
      });

      if (chooserEvent2) {
        console.log("File chooser opened on second try!");
        await send("Page.handleFileChooser", {
          action: "accept",
          files: [photoPath]
        });
        console.log("File accepted!");
        await sleep(5000);
      } else {
        console.log("File chooser still not opening");

        // Last resort: set files directly on the file input
        console.log("\nFalling back to DOM.setFileInputFiles...");
        const docResult = await send("DOM.getDocument");
        const searchResult = await send("DOM.querySelectorAll", {
          nodeId: docResult.root.nodeId,
          selector: 'input[type="file"]'
        });

        if (searchResult.nodeIds?.length > 0) {
          await send("DOM.setFileInputFiles", {
            nodeId: searchResult.nodeIds[0],
            files: [photoPath]
          });
          console.log("Files set via DOM.setFileInputFiles");

          // Trigger change event
          await eval_(`
            const fileInput = document.querySelector('input[type="file"]');
            if (fileInput) {
              fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
          `);
          await sleep(3000);
        }
      }
    }
  }

  // Disable interception
  try {
    await send("Page.setInterceptFileChooserDialog", { enabled: false });
  } catch(e) {}

  // Check result
  console.log("\n=== Upload result ===");
  r = await eval_(`
    const errors = Array.from(document.querySelectorAll('*'))
      .filter(el => el.textContent?.includes('upload at least') && el.children.length === 0 && el.offsetParent !== null)
      .map(el => el.textContent.trim());

    const uploadArea = document.querySelector('.profile-picture-uploader, [class*="profile-picture"]');

    return JSON.stringify({
      errors,
      uploadAreaText: uploadArea?.textContent?.trim()?.substring(0, 200) || '',
      hasImage: !!document.querySelector('.profile-picture img, [class*="profile-picture"] img, .plupload img'),
      fileInputFiles: document.querySelector('input[type="file"]')?.files?.length || 0
    });
  `);
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
