// Navigate to profile and find avatar upload mechanism
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));
import fs from 'fs';
import path from 'path';

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

  // First, navigate to user's own profile
  console.log("Navigating to /u/weberg5...");
  await send("Page.navigate", { url: "https://www.freelancer.com/u/weberg5" });
  await sleep(4000);

  let r = await eval_(`
    return JSON.stringify({
      url: location.href,
      preview: document.body.innerText.substring(0, 1000),
      editBtns: Array.from(document.querySelectorAll('a, button, [role="button"]'))
        .filter(el => el.offsetParent !== null)
        .filter(el => {
          const t = el.textContent?.trim()?.toLowerCase() || '';
          const c = el.className?.toString()?.toLowerCase() || '';
          return t.includes('edit') || t.includes('upload') || t.includes('change') ||
                 c.includes('edit') || c.includes('pencil') || c.includes('camera');
        })
        .map(el => ({
          tag: el.tagName,
          text: el.textContent.trim().substring(0, 40),
          href: el.href?.substring(0, 80) || '',
          class: el.className?.toString()?.substring(0, 60)
        }))
    });
  `);
  console.log("Profile page:", r);

  const profileState = JSON.parse(r);

  // If profile exists, look for avatar click area
  if (!profileState.preview.includes("doesn't exist")) {
    console.log("\nProfile page loaded. Looking for avatar area...");
    r = await eval_(`
      const avatarArea = document.querySelector('[class*="ProfileAvatar" i], [class*="avatar" i][class*="edit" i], [class*="avatar" i]');
      const allClickableNearAvatar = Array.from(document.querySelectorAll('[class*="avatar" i], [class*="Avatar" i]'))
        .map(el => ({
          tag: el.tagName,
          class: el.className?.toString()?.substring(0, 80),
          children: el.children.length,
          hasFileInput: !!el.querySelector('input[type="file"]'),
          rect: (() => { const r = el.getBoundingClientRect(); return { x: r.x + r.width/2, y: r.y + r.height/2, w: r.width, h: r.height }; })()
        }));
      return JSON.stringify(allClickableNearAvatar);
    `);
    console.log("Avatar elements:", r);
  }

  // Try the settings/profile page - maybe with a different URL pattern
  console.log("\nTrying /settings page...");
  await send("Page.navigate", { url: "https://www.freelancer.com/settings" });
  await sleep(3000);
  r = await eval_(`return JSON.stringify({ url: location.href, preview: document.body.innerText.substring(0, 500) })`);
  console.log("Settings:", r);

  // Try account settings
  console.log("\nTrying account settings...");
  await send("Page.navigate", { url: "https://www.freelancer.com/users/settings" });
  await sleep(3000);
  r = await eval_(`return JSON.stringify({ url: location.href, preview: document.body.innerText.substring(0, 500) })`);
  console.log("User settings:", r);

  // Try the Freelancer API to upload avatar
  // First, get the oauth token from cookies
  console.log("\n=== Trying API approach ===");
  r = await eval_(`
    // Get cookies and token
    const cookies = document.cookie;
    const csrfMeta = document.querySelector('meta[name="csrf-token"]');
    const csrfToken = csrfMeta?.content;

    // Try to get CSRF from Freelancer's Angular app
    const flApp = window.__INITIAL_STATE__ || window.__freelancer_initial_state__;

    // Try getting any auth tokens from session storage or local storage
    let authToken = null;
    try {
      authToken = localStorage.getItem('access_token') || localStorage.getItem('token') ||
                  sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
    } catch(e) {}

    // Check for cookie with token
    const cookieObj = {};
    cookies.split(';').forEach(c => {
      const [k, v] = c.trim().split('=');
      cookieObj[k] = v;
    });

    return JSON.stringify({
      hasCookies: cookies.length > 0,
      csrfToken: csrfToken || 'none',
      authToken: authToken ? authToken.substring(0, 30) + '...' : 'none',
      cookieKeys: Object.keys(cookieObj).filter(k => k.includes('token') || k.includes('session') || k.includes('auth') || k.includes('XSRF'))
    });
  `);
  console.log("Auth info:", r);

  // Use fetch API from within the page to upload the avatar
  // First, read the photo and convert to base64
  const photoPath = "D:\\007 - DOCUMENTS TO BE FILED\\Weber Files\\Weber's Photo.jpg";
  const photoBuffer = fs.readFileSync(photoPath);
  const base64Photo = photoBuffer.toString('base64');
  console.log(`\nPhoto loaded: ${photoBuffer.length} bytes, base64: ${base64Photo.length} chars`);

  // Upload via Freelancer's internal API using fetch from the page context
  console.log("\nUploading via internal API...");
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        // Convert base64 to blob
        const base64 = ${JSON.stringify(base64Photo)};
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'image/jpeg' });

        // Create FormData
        const formData = new FormData();
        formData.append('file', blob, 'photo.jpg');

        // Try Freelancer's avatar upload API
        const response = await fetch('/api/users/0.1/self/avatar', {
          method: 'PUT',
          body: formData,
          credentials: 'include'
        });

        const text = await response.text();
        resolve(JSON.stringify({
          status: response.status,
          statusText: response.statusText,
          body: text.substring(0, 500)
        }));
      } catch(e) {
        resolve(JSON.stringify({ error: e.message }));
      }
    });
  `);
  console.log("API upload result:", r);

  // If that didn't work, try other API endpoints
  const apiResult = JSON.parse(r);
  if (apiResult.status !== 200) {
    console.log("\nTrying alternative API endpoint...");
    r = await eval_(`
      return new Promise(async (resolve) => {
        try {
          const base64 = ${JSON.stringify(base64Photo)};
          const binary = atob(base64);
          const bytes = new Uint8Array(binary.length);
          for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
          const blob = new Blob([bytes], { type: 'image/jpeg' });

          const formData = new FormData();
          formData.append('avatar', blob, 'photo.jpg');

          // Try POST to users API
          const response = await fetch('/api/users/0.1/self/', {
            method: 'PUT',
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
    console.log("Alt API result:", r);
  }

  // Try yet another approach - multipart upload to the profile photo endpoint
  console.log("\nTrying profile photo endpoint...");
  r = await eval_(`
    return new Promise(async (resolve) => {
      try {
        const base64 = ${JSON.stringify(base64Photo)};
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const blob = new Blob([bytes], { type: 'image/jpeg' });

        const formData = new FormData();
        formData.append('profile_image', blob, 'photo.jpg');

        // Try the profile image upload endpoint
        const response = await fetch('/api/users/0.1/self/profile_image', {
          method: 'POST',
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
  console.log("Profile image API:", r);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
