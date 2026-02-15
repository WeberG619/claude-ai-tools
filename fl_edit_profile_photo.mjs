// Click "Edit profile" on /u/weberg5 and upload photo
import fs from 'fs';

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

  // Navigate to profile page
  await send("Page.navigate", { url: "https://www.freelancer.com/u/weberg5" });
  await sleep(4000);

  // Click "Edit profile"
  let r = await eval_(`
    const editBtn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Edit profile' && b.offsetParent !== null);
    if (editBtn) {
      editBtn.scrollIntoView({ block: 'center' });
      const rect = editBtn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);
  console.log("Edit profile button:", r);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(3000);
  }

  // Check what loaded
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      fileInputs: Array.from(document.querySelectorAll('input[type="file"]')).map(f => ({
        id: f.id, name: f.name, accept: f.accept,
        class: f.className?.substring(0, 50),
        parentClass: f.parentElement?.className?.substring(0, 50)
      })),
      modals: Array.from(document.querySelectorAll('[class*="modal" i], [class*="Modal" i], [class*="drawer" i], [class*="Drawer" i], [class*="sidebar" i], [class*="Sidebar" i], [class*="panel" i], [class*="Panel" i]'))
        .filter(el => window.getComputedStyle(el).display !== 'none')
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 80),
          hasFileInput: !!el.querySelector('input[type="file"]')
        })),
      buttons: Array.from(document.querySelectorAll('button'))
        .filter(b => b.offsetParent !== null)
        .map(b => b.textContent.trim().substring(0, 40)),
      avatarEls: Array.from(document.querySelectorAll('[class*="avatar" i], [class*="Avatar" i], [class*="photo" i], [class*="Photo" i]'))
        .filter(el => el.offsetParent !== null)
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 60),
          clickable: el.style.cursor === 'pointer' || el.tagName === 'BUTTON' || el.tagName === 'A'
        })),
      preview: document.body.innerText.substring(0, 1500)
    });
  `);
  console.log("\nAfter clicking Edit profile:", r);

  const state = JSON.parse(r);

  // If we have file inputs, use them
  if (state.fileInputs.length > 0) {
    console.log("\n=== Found file input! ===");
    await send("DOM.enable");
    await send("DOM.getDocument");

    const evalResult = await send("Runtime.evaluate", {
      expression: `document.querySelector('input[type="file"]')`,
      returnByValue: false
    });
    if (evalResult.result?.objectId) {
      const nodeResult = await send("DOM.requestNode", { objectId: evalResult.result.objectId });
      if (nodeResult.nodeId) {
        const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
        console.log(`Uploading: ${photoPath}`);
        await send("DOM.setFileInputFiles", { nodeId: nodeResult.nodeId, files: [photoPath] });
        console.log("File set!");
        await sleep(5000);
      }
    }
  } else {
    // Click on the avatar area to see if it opens a file picker
    console.log("\nNo file input yet. Trying to click avatar area...");
    r = await eval_(`
      // Find the large avatar on the profile edit page
      const avatars = Array.from(document.querySelectorAll('[class*="avatar" i], [class*="Avatar" i]'))
        .filter(el => {
          const rect = el.getBoundingClientRect();
          return rect.width > 50 && rect.height > 50;  // Large avatar only
        })
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 60),
          rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, w: r.width }; })()
        }));
      return JSON.stringify(avatars);
    `);
    console.log("Large avatars:", r);

    const avatars = JSON.parse(r);
    if (avatars.length > 0) {
      // Click the largest avatar
      const largest = avatars.sort((a, b) => b.rect.w - a.rect.w)[0];
      console.log(`Clicking avatar (${largest.rect.w}px)...`);
      await send("Input.dispatchMouseEvent", { type: "mousePressed", x: largest.rect.x, y: largest.rect.y, button: "left", clickCount: 1 });
      await sleep(50);
      await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: largest.rect.x, y: largest.rect.y, button: "left", clickCount: 1 });
      await sleep(3000);

      // Check for file input or modal
      r = await eval_(`
        const fi = document.querySelectorAll('input[type="file"]').length;
        const modals = Array.from(document.querySelectorAll('[class*="modal" i], [class*="Modal" i]'))
          .filter(el => window.getComputedStyle(el).display !== 'none')
          .map(el => el.textContent?.trim()?.substring(0, 200));
        const btns = Array.from(document.querySelectorAll('button'))
          .filter(b => b.offsetParent !== null)
          .map(b => b.textContent.trim());
        return JSON.stringify({ fileInputs: fi, modals, buttons: btns });
      `);
      console.log("After clicking avatar:", r);
    }

    // Try the API approach with proper XSRF token
    console.log("\n=== Trying API with XSRF token ===");
    const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
    const photoBuffer = fs.readFileSync(photoPath);
    const base64Photo = photoBuffer.toString('base64');
    console.log(`Photo: ${photoBuffer.length} bytes`);

    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          // Get XSRF token from cookie
          const xsrfMatch = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
          const xsrfToken = xsrfMatch ? decodeURIComponent(xsrfMatch[1]) : null;

          const base64 = ${JSON.stringify(base64Photo)};
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'image/jpeg' });

          const formData = new FormData();
          formData.append('file', blob, 'photo.jpg');

          // Try with XSRF token header
          const headers = {};
          if (xsrfToken) headers['X-XSRF-TOKEN'] = xsrfToken;
          headers['freelancer-oauth-v1'] = document.cookie.match(/session2=([^;]+)/)?.[1] || '';

          const response = await fetch('/api/users/0.1/self/', {
            method: 'PUT',
            headers: headers,
            body: formData,
            credentials: 'include'
          });

          const text = await response.text();
          resolve(JSON.stringify({ status: response.status, xsrfFound: !!xsrfToken, body: text.substring(0, 500) }));
        } catch(e) {
          resolve(JSON.stringify({ error: e.message }));
        }
      });
    `);
    console.log("API with XSRF:", r);

    // Try different approach - use the webapp's internal upload mechanism
    console.log("\nTrying webapp internal upload via XHR...");
    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          const base64 = ${JSON.stringify(base64Photo)};
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'image/jpeg' });

          const formData = new FormData();
          formData.append('file', blob, 'photo.jpg');

          // Get XSRF from cookie
          const xsrfMatch = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
          const xsrfToken = xsrfMatch ? decodeURIComponent(xsrfMatch[1]) : '';

          const response = await fetch('https://www.freelancer.com/api/users/0.1/self/avatar.json', {
            method: 'POST',
            headers: {
              'X-XSRF-TOKEN': xsrfToken,
            },
            body: formData,
            credentials: 'include'
          });

          const text = await response.text();
          resolve(JSON.stringify({ status: response.status, body: text.substring(0, 500) }));
        } catch(e) {
          resolve(JSON.stringify({ error: e.message }));
        }
      });
    `);
    console.log("Avatar.json endpoint:", r);

    // Try the multipart upload endpoint that Freelancer actually uses
    console.log("\nTrying Freelancer file upload endpoint...");
    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          const base64 = ${JSON.stringify(base64Photo)};
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'image/jpeg' });

          const formData = new FormData();
          formData.append('file', blob, 'photo.jpg');

          const xsrfMatch = document.cookie.match(/XSRF-TOKEN=([^;]+)/);
          const xsrfToken = xsrfMatch ? decodeURIComponent(xsrfMatch[1]) : '';

          // Try upload endpoint
          const response = await fetch('https://www.freelancer.com/api/files/0.1/upload/', {
            method: 'POST',
            headers: { 'X-XSRF-TOKEN': xsrfToken },
            body: formData,
            credentials: 'include'
          });

          const text = await response.text();
          resolve(JSON.stringify({ status: response.status, body: text.substring(0, 500) }));
        } catch(e) {
          resolve(JSON.stringify({ error: e.message }));
        }
      });
    `);
    console.log("File upload endpoint:", r);
  }

  // Check final state
  r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 500)
    });
  `);
  console.log("\n=== FINAL ===");
  console.log(r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
