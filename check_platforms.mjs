const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function connectToPage(urlMatch) {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();
  const tab = tabs.find(t => t.type === "page" && t.url.includes(urlMatch));
  if (!tab) return null;
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
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  // Check Outlier.ai
  console.log("========== OUTLIER.AI ==========");
  let conn = await connectToPage("outlier.ai");
  if (conn) {
    let r = await conn.eval_(`return window.location.href`);
    console.log("URL:", r);
    r = await conn.eval_(`
      const body = document.body.innerText;
      return body.substring(0, 4000);
    `);
    console.log(r);
    conn.ws.close();
  } else {
    console.log("No Outlier.ai tab found");
  }

  await sleep(500);

  // Check PeoplePerHour
  console.log("\\n\\n========== PEOPLEPERHOUR ==========");
  conn = await connectToPage("peopleperhour.com");
  if (conn) {
    let r = await conn.eval_(`return window.location.href`);
    console.log("URL:", r);

    // Navigate to dashboard to check status
    await conn.eval_(`window.location.href = 'https://www.peopleperhour.com/dashboard/seller'`);
    await sleep(4000);
    conn.ws.close(); await sleep(1000);
    conn = await connectToPage("peopleperhour.com");
    if (conn) {
      r = await conn.eval_(`
        const body = document.body.innerText;
        return body.substring(0, 4000);
      `);
      console.log(r);

      // Check for proposals/credits
      r = await conn.eval_(`
        const text = document.body.innerText;
        const proposalMatch = text.match(/proposal.*?(\\d+)/i);
        const creditMatch = text.match(/credit.*?(\\d+)/i);
        return JSON.stringify({
          proposals: proposalMatch ? proposalMatch[0] : 'unknown',
          credits: creditMatch ? creditMatch[0] : 'unknown'
        });
      `);
      console.log("\\nCredits info:", r);
      conn.ws.close();
    }
  } else {
    console.log("No PeoplePerHour tab found");
  }
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
