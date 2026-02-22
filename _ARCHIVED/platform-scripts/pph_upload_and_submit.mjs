// Upload resized photo to PPH and submit application
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
  const photoPath = "D:\\_CLAUDE-TOOLS\\weber_profile_photo.jpg";

  const { ws, send, eval_ } = await connectToPage("peopleperhour.com");
  console.log("Connected\n");

  await send("DOM.enable");
  await send("Page.enable");

  // Step 1: Set file on the input via DOM API
  console.log("=== Setting file via DOM.setFileInputFiles ===");
  const docResult = await send("DOM.getDocument");
  const searchResult = await send("DOM.querySelectorAll", {
    nodeId: docResult.root.nodeId,
    selector: 'input[type="file"]'
  });

  if (!searchResult.nodeIds?.length) {
    console.log("No file input found!");
    ws.close();
    return;
  }

  console.log(`Found ${searchResult.nodeIds.length} file input(s)`);

  // Set files
  await send("DOM.setFileInputFiles", {
    nodeId: searchResult.nodeIds[0],
    files: [photoPath]
  });
  console.log("File set on input");

  // Trigger change event to kick off Plupload
  await eval_(`
    const fileInput = document.querySelector('input[type="file"]');
    if (fileInput) {
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  `);
  console.log("Change event dispatched");
  await sleep(3000);

  // Check if Plupload picked it up
  let r = await eval_(`
    const uploadArea = document.querySelector('.attachFiles-dropArea');
    const fileItems = document.querySelectorAll('.plupload_file_name, [class*="file-item"], [class*="attachment"]');
    const errors = Array.from(document.querySelectorAll('*'))
      .filter(el => el.children.length === 0 && el.offsetParent !== null && el.textContent?.includes('upload at least'))
      .map(el => el.textContent.trim());

    return JSON.stringify({
      fileItems: fileItems.length,
      errors,
      uploadAreaText: uploadArea?.textContent?.trim()?.substring(0, 200) || '',
      bodyHasUploadError: (document.body?.innerText || '').includes('upload at least')
    });
  `);
  console.log("After change event:", r);

  const afterChange = JSON.parse(r);

  // If Plupload didn't pick it up, try alternative: create a File object and use DataTransfer
  if (afterChange.bodyHasUploadError || afterChange.fileItems === 0) {
    console.log("\nPlupload didn't process - trying DataTransfer approach...");

    // Use fetch to load the image as a blob, then create a File and set on input
    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          // Create a canvas with a simple image as fallback
          // First try to read the file from the input
          const fileInput = document.querySelector('input[type="file"]');
          if (fileInput && fileInput.files.length > 0) {
            resolve('has files: ' + fileInput.files[0].name + ' (' + fileInput.files[0].size + ' bytes)');
            return;
          }
          resolve('no files on input');
        } catch(e) {
          resolve('error: ' + e.message);
        }
      });
    `);
    console.log("File input state:", r);

    // Try Method 2: Use Page.setInterceptFileChooserDialog
    console.log("\nTrying file chooser interception...");
    await send("Page.setInterceptFileChooserDialog", { enabled: true });

    // Listen for file chooser
    let chooserResolved = false;
    const chooserPromise = new Promise((resolve) => {
      const handler = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.method === "Page.fileChooserOpened") {
          chooserResolved = true;
          resolve(msg.params);
          ws.removeEventListener("message", handler);
        }
      };
      ws.addEventListener("message", handler);
      setTimeout(() => {
        if (!chooserResolved) {
          ws.removeEventListener("message", handler);
          resolve(null);
        }
      }, 6000);
    });

    // Click the browse link - find and click it precisely
    r = await eval_(`
      // Find the "browse" link in the upload area
      const links = Array.from(document.querySelectorAll('a'));
      const browseLink = links.find(a =>
        a.textContent.trim().toLowerCase() === 'browse' ||
        a.className.includes('attachFiles-pick')
      );

      if (browseLink) {
        // Get its coordinates for CDP click
        const rect = browseLink.getBoundingClientRect();
        return JSON.stringify({
          found: true,
          text: browseLink.textContent.trim(),
          class: browseLink.className.substring(0, 60),
          x: rect.x + rect.width/2,
          y: rect.y + rect.height/2
        });
      }

      // Also try the Plupload container itself
      const container = document.getElementById('attachFiles-box-MemberProfile_images');
      if (container) {
        const rect = container.getBoundingClientRect();
        return JSON.stringify({
          found: true, text: 'container',
          x: rect.x + rect.width/2,
          y: rect.y + rect.height/2
        });
      }

      return JSON.stringify({ found: false });
    `);
    console.log("Browse element:", r);

    const browseInfo = JSON.parse(r);
    if (browseInfo.found) {
      // Use CDP mouse click on the browse element
      console.log(`Clicking at (${browseInfo.x}, ${browseInfo.y})...`);
      await send("Input.dispatchMouseEvent", {
        type: "mousePressed", x: browseInfo.x, y: browseInfo.y,
        button: "left", clickCount: 1
      });
      await sleep(50);
      await send("Input.dispatchMouseEvent", {
        type: "mouseReleased", x: browseInfo.x, y: browseInfo.y,
        button: "left", clickCount: 1
      });

      const chooserEvent = await chooserPromise;
      if (chooserEvent) {
        console.log("File chooser opened! Accepting file...");
        await send("Page.handleFileChooser", {
          action: "accept",
          files: [photoPath]
        });
        console.log("File accepted via file chooser!");
        await sleep(5000);
      } else {
        console.log("File chooser didn't open");
      }
    }

    try {
      await send("Page.setInterceptFileChooserDialog", { enabled: false });
    } catch(e) {}
  }

  // Step 2: Check upload result and verify all fields
  console.log("\n=== Checking state ===");
  await sleep(2000);
  r = await eval_(`
    const $ = jQuery;
    const uploadError = Array.from(document.querySelectorAll('*'))
      .filter(el => el.children.length === 0 && el.offsetParent !== null && el.textContent?.includes('upload at least'))
      .length > 0;

    return JSON.stringify({
      uploadError,
      jobTitle: document.getElementById('MemberProfile_job_title')?.value || '',
      aboutLen: (document.getElementById('MemberProfile_about')?.value || '').length,
      rate: document.getElementById('MemberProfile_real_hour_rate')?.value || '',
      skillCount: (() => { try { return ($('#SellerShowCase_topSkillsList').select2('data') || []).length; } catch(e) { return 0; } })(),
      langCount: (() => { try { return ($('#SellerShowCase_languagesString').select2('data') || []).length; } catch(e) { return 0; } })(),
      allErrors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary, .help-inline'))
        .filter(el => el.offsetParent !== null)
        .map(el => el.textContent.trim().substring(0, 100))
        .filter(t => t.length > 3)
    });
  `);
  console.log(r);

  const state = JSON.parse(r);

  // Step 3: Submit if no upload error, or report what's still needed
  if (!state.uploadError && state.jobTitle && state.skillCount > 0 && state.langCount > 0 && state.rate) {
    console.log("\n=== ALL GOOD - SUBMITTING ===");
    r = await eval_(`
      const btn = document.querySelector('button[type="submit"], input[type="submit"]');
      if (btn && !btn.disabled) {
        btn.scrollIntoView({ block: 'center' });
        const rect = btn.getBoundingClientRect();
        return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2, text: btn.textContent?.trim() || btn.value });
      }
      return null;
    `);

    if (r) {
      const btn = JSON.parse(r);
      console.log(`Clicking "${btn.text}"...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: btn.x, y: btn.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: btn.x, y: btn.y, button: "left", clickCount: 1 });
      await sleep(8000);

      r = await eval_(`
        return JSON.stringify({
          url: location.href,
          errors: Array.from(document.querySelectorAll('[class*="error" i], .errorSummary'))
            .filter(el => el.offsetParent !== null)
            .map(el => el.textContent.trim().substring(0, 150))
            .filter(t => t.length > 3),
          preview: document.body?.innerText?.substring(0, 1000)
        });
      `);
      console.log("Submit result:", r);
    }
  } else {
    console.log("\nCannot submit yet:");
    if (state.uploadError) console.log("  - Profile photo still required");
    if (!state.jobTitle) console.log("  - Job title missing");
    if (state.skillCount === 0) console.log("  - Skills missing");
    if (state.langCount === 0) console.log("  - Language missing");
    if (!state.rate) console.log("  - Rate missing");
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
