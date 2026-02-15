// Fill out Guru.com profile via CDP
// Connects to Chrome localhost:9222 and interacts with the Guru profile page
// Uses built-in WebSocket (Node 22+) with addEventListener API

const CDP_HTTP = "http://localhost:9222";

async function getGuruTab() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  const guru = tabs.find(t => t.url.includes("guru.com"));
  if (!guru) throw new Error("No Guru.com tab found!");
  console.log(`Found Guru tab: ${guru.title} - ${guru.url}`);
  return guru;
}

async function connectTab(tab) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    let id = 1;
    const pending = new Map();

    ws.addEventListener("open", () => {
      console.log("Connected to tab WebSocket");
      const send = (method, params = {}) => {
        return new Promise((res, rej) => {
          const msgId = id++;
          pending.set(msgId, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id: msgId, method, params }));
        });
      };
      resolve({ ws, send });
    });

    ws.addEventListener("message", (event) => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) p.reject(new Error(msg.error.message));
        else p.resolve(msg.result);
      }
    });

    ws.addEventListener("error", (e) => reject(new Error("WebSocket error")));
  });
}

async function evaluate(send, expression) {
  const result = await send("Runtime.evaluate", {
    expression,
    returnByValue: true,
    awaitPromise: true,
  });
  if (result.exceptionDetails) {
    throw new Error(result.exceptionDetails.text || JSON.stringify(result.exceptionDetails));
  }
  return result.result?.value;
}

function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const tab = await getGuruTab();
  const { ws, send } = await connectTab(tab);

  try {
    // Step 1: Click "Add a Service" radio button
    console.log("\n--- Step 1: Click 'Add a Service' ---");
    const clickResult = await evaluate(send, `
      const radio = document.querySelector('input[type="radio"]');
      if (radio) { radio.click(); "clicked radio"; } else { "no radio found"; }
    `);
    console.log("Result:", clickResult);
    await sleep(2000);

    // Take a snapshot of what's on the page now
    console.log("\n--- Checking page state after click ---");
    const pageState = await evaluate(send, `
      // Get all visible form elements
      const inputs = Array.from(document.querySelectorAll('input, select, textarea'));
      const labels = Array.from(document.querySelectorAll('label'));
      const buttons = Array.from(document.querySelectorAll('button, input[type="submit"]'));

      JSON.stringify({
        url: location.href,
        inputs: inputs.map(i => ({
          type: i.type || i.tagName,
          name: i.name,
          id: i.id,
          placeholder: i.placeholder,
          value: i.value,
          visible: i.offsetParent !== null
        })).filter(i => i.visible),
        labels: labels.map(l => l.textContent.trim()).filter(t => t),
        buttons: buttons.map(b => ({
          text: b.textContent?.trim() || b.value,
          type: b.type,
          visible: b.offsetParent !== null
        })).filter(b => b.visible),
        headings: Array.from(document.querySelectorAll('h1,h2,h3,h4')).map(h => h.textContent.trim()),
        selects: Array.from(document.querySelectorAll('select')).map(s => ({
          name: s.name,
          id: s.id,
          options: Array.from(s.options).slice(0, 15).map(o => ({ value: o.value, text: o.text }))
        }))
      }, null, 2);
    `);

    console.log("Page state:", pageState);

  } finally {
    ws.close();
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
