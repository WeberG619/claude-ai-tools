// Check current state of Guru.com page
const CDP_HTTP = "http://localhost:9222";

async function run() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) { console.log("No Guru tab found"); return; }
  console.log("Tab:", guru.title, "-", guru.url);

  const ws = new WebSocket(guru.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener("open", r));

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
    return r.result?.value;
  };

  // Check the main content area
  const state = await eval_(`
    const mainContent = document.querySelector('.main-content, .profile-content, [class*="content"]')
      || document.querySelector('.container') || document.body;

    // Get visible text
    const bodyText = document.body.innerText.substring(0, 3000);

    // Check for any forms, iframes, or dynamic content
    const iframes = Array.from(document.querySelectorAll('iframe')).map(f => f.src);
    const forms = Array.from(document.querySelectorAll('form')).map(f => ({ action: f.action, id: f.id }));
    const alerts = Array.from(document.querySelectorAll('.alert, .notification, .message, .success, .error'))
      .map(a => a.textContent.trim());

    return JSON.stringify({
      url: location.href,
      bodyTextPreview: bodyText.substring(0, 1500),
      iframes: iframes,
      forms: forms,
      alerts: alerts
    }, null, 2);
  `);

  console.log("State:", state);
  ws.close();
}

run().catch(e => console.error("Error:", e.message));
