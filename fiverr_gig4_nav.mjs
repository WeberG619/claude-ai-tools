// Navigate to create new gig from the manage_gigs page
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
  let { ws, send, eval_ } = await connectToPage("fiverr.com");
  console.log("Connected\n");

  let r = await eval_(`return location.href`);
  console.log("Current URL:", r);

  // Look for "Create a New Gig" button or link
  r = await eval_(`
    const links = Array.from(document.querySelectorAll('a, button'))
      .filter(el => el.offsetParent !== null && el.textContent.trim().length > 0 && el.textContent.trim().length < 40)
      .filter(el => {
        const text = el.textContent.trim().toLowerCase();
        return text.includes('create') || text.includes('new gig') || text.includes('add gig');
      })
      .map(el => ({
        text: el.textContent.trim(),
        tag: el.tagName,
        href: el.href || '',
        x: Math.round(el.getBoundingClientRect().x + el.getBoundingClientRect().width/2),
        y: Math.round(el.getBoundingClientRect().y + el.getBoundingClientRect().height/2)
      }));
    return JSON.stringify(links);
  `);
  console.log("Create buttons:", r);
  const createBtns = JSON.parse(r);

  if (createBtns.length > 0) {
    const btn = createBtns[0];
    if (btn.href) {
      console.log(`Navigating to: ${btn.href}`);
      await eval_(`window.location.href = '${btn.href}'`);
    } else {
      console.log(`Clicking "${btn.text}" at (${btn.x}, ${btn.y})`);
      await clickAt(send, btn.x, btn.y);
    }
    await sleep(5000);
    ws.close();
    await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("fiverr.com"));

    r = await eval_(`
      return JSON.stringify({
        url: location.href,
        wizard: new URL(location.href).searchParams.get('wizard'),
        body: document.body.innerText.substring(0, 300)
      });
    `);
    console.log("After click:", r);
  } else {
    console.log("No create button found. Dumping all links...");
    r = await eval_(`
      return Array.from(document.querySelectorAll('a'))
        .filter(el => el.href && el.href.includes('gig'))
        .map(el => el.href + ' | ' + el.textContent.trim().substring(0, 30))
        .join('\\n');
    `);
    console.log("Gig links:\n", r);

    // Also show page text
    r = await eval_(`return document.body.innerText.substring(0, 800)`);
    console.log("\nPage text:", r);
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
