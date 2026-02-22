// Search for jobs on Upwork matching Weber's skills
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
      expression: `(async () => { ${expr} })()`,
      returnByValue: true, awaitPromise: true
    });
    if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
    return r.result?.value;
  };
  return { ws, send, eval_ };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  // Navigate to find work / job search
  await eval_(`window.location.href = 'https://www.upwork.com/nx/find-work/'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  ({ ws, send, eval_ } = await connectToPage("upwork.com"));

  let r = await eval_(`return JSON.stringify({
    url: location.href,
    title: document.title
  })`);
  console.log("Page:", r);

  // Get recommended/best matches jobs
  r = await eval_(`
    // Look for job cards
    const jobCards = Array.from(document.querySelectorAll('[data-test="job-tile-list"] > *, [class*="job-tile"], article, [data-test="JobTile"]'))
      .filter(el => el.offsetParent !== null)
      .slice(0, 10)
      .map(el => ({
        text: el.textContent.trim().substring(0, 300),
        tag: el.tagName,
        class: (el.className || '').substring(0, 50)
      }));
    return JSON.stringify({ count: jobCards.length, cards: jobCards });
  `);
  console.log("Job cards:", r);

  // Get full page text for job listings
  r = await eval_(`
    const text = document.body.innerText;
    return text.substring(0, 3000);
  `);
  console.log("\nPage content:");
  console.log(r);

  // Also search for specific categories
  // Search for BIM/Revit jobs
  console.log("\n\n=== Searching for specific job categories ===\n");
  
  const searches = ['Revit BIM', 'technical writing', 'data entry'];
  
  for (const query of searches) {
    await eval_(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=' + encodeURIComponent('${query}') + '&sort=recency'`);
    await sleep(4000);
    ws.close(); await sleep(1000);
    ({ ws, send, eval_ } = await connectToPage("upwork.com"));

    r = await eval_(`
      // Extract job listings
      const sections = document.querySelectorAll('section[data-test="JobTile"], [data-test="job-tile-list"] section, article');
      const jobs = [];
      
      // Try different selectors for job titles and details
      const allText = document.body.innerText;
      
      // Find job title elements
      const titles = Array.from(document.querySelectorAll('a[data-test="job-tile-title-link"], h2 a, [class*="job-title"] a'))
        .filter(el => el.offsetParent !== null)
        .slice(0, 8)
        .map(el => ({
          title: el.textContent.trim().substring(0, 80),
          href: el.href
        }));
      
      return JSON.stringify({
        query: '${query}',
        titleCount: titles.length,
        titles,
        bodySnippet: allText.substring(0, 2000)
      });
    `);
    const result = JSON.parse(r);
    console.log(`\n--- ${query.toUpperCase()} (${result.titleCount} jobs found) ---`);
    if (result.titles.length > 0) {
      result.titles.forEach((t, i) => {
        console.log(`  ${i+1}. ${t.title}`);
      });
    } else {
      // Parse from body text
      console.log(result.bodySnippet.substring(0, 800));
    }
  }

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
