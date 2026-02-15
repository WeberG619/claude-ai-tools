// Create Fiverr Gig: MCP Server Development
// Uses CDP websocket to automate gig creation
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToFiverrTab() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  // Find the Fiverr manage_gigs page tab
  let tab = tabs.find(t => t.type === "page" && t.url.includes("fiverr.com"));
  if (!tab) throw new Error("No Fiverr tab found. Open Fiverr first.");
  console.log(`Connected to: ${tab.title} | ${tab.url}`);

  const ws = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((res, rej) => {
    ws.addEventListener("open", res);
    ws.addEventListener("error", rej);
  });

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
      expression: expr,
      returnByValue: true,
      awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };

  const navigate = async (url) => {
    await send("Page.navigate", { url });
    await sleep(3000);
  };

  return { ws, send, eval_, navigate };
}

async function main() {
  console.log("Connecting to Fiverr tab via CDP...");
  const { ws, send, eval_, navigate } = await connectToFiverrTab();

  // Step 1: Navigate to new gig creation
  console.log("Navigating to gig creation...");
  await navigate("https://www.fiverr.com/manage_gigs/new");
  await sleep(3000);

  // Check current URL to see where we landed
  const currentUrl = await eval_(`window.location.href`);
  console.log(`Current URL: ${currentUrl}`);

  if (currentUrl.includes("manage_gigs/new") || currentUrl.includes("gig_wizard")) {
    console.log("On gig creation page. Filling overview...");

    // Wait for the title input to appear
    await sleep(2000);

    // Find and fill the gig title
    // Fiverr gig titles must start with "I will"
    const title = "I will build a custom MCP server to connect AI to your software";

    const filled = await eval_(`
      (async () => {
        // Try to find the title input
        const titleInput = document.querySelector('input[name="title"]') ||
                          document.querySelector('textarea[name="title"]') ||
                          document.querySelector('[class*="title"] input') ||
                          document.querySelector('[class*="title"] textarea') ||
                          document.querySelector('[data-testid*="title"]') ||
                          document.querySelector('.gig-title input') ||
                          document.querySelector('#title');

        if (titleInput) {
          titleInput.focus();
          titleInput.value = "";
          // Use native input setter to trigger React state
          const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
          )?.set || Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype, 'value'
          )?.set;
          if (nativeInputValueSetter) {
            nativeInputValueSetter.call(titleInput, "${title}");
          } else {
            titleInput.value = "${title}";
          }
          titleInput.dispatchEvent(new Event('input', { bubbles: true }));
          titleInput.dispatchEvent(new Event('change', { bubbles: true }));
          return "title_filled";
        }

        // Log what we see on the page for debugging
        const inputs = Array.from(document.querySelectorAll('input, textarea'));
        const inputInfo = inputs.map(i => ({
          tag: i.tagName,
          name: i.name,
          id: i.id,
          class: i.className.substring(0, 50),
          placeholder: i.placeholder?.substring(0, 50)
        }));
        return JSON.stringify({ status: "no_title_input", inputs: inputInfo.slice(0, 10) });
      })()
    `);

    console.log("Fill result:", filled);

  } else {
    console.log("Not on expected page. Let me check what's here...");
    const pageInfo = await eval_(`
      JSON.stringify({
        url: window.location.href,
        title: document.title,
        h1: document.querySelector('h1')?.textContent || 'none',
        buttons: Array.from(document.querySelectorAll('button, a[class*="create"], a[class*="new"]'))
          .slice(0, 5)
          .map(b => ({ text: b.textContent?.trim().substring(0, 50), href: b.href || '' }))
      })
    `);
    console.log("Page info:", pageInfo);
  }

  // Close websocket
  ws.close();
  console.log("Done.");
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
