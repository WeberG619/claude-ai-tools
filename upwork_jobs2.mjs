// Search for quick jobs: writing, data entry, VA, proofreading
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

async function searchJobs(ws, send, eval_, query) {
  await eval_(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=' + encodeURIComponent('${query}') + '&sort=recency&payment_verified=1'`);
  await sleep(5000);
  ws.close(); await sleep(1000);
  const conn = await connectToPage("upwork.com");
  ws = conn.ws; send = conn.send; eval_ = conn.eval_;

  const r = await eval_(`
    // Get job tiles with full details
    const jobSections = Array.from(document.querySelectorAll('section[data-test="JobTile"], [data-test="job-tile-list"] > section'))
      .filter(el => el.offsetParent !== null)
      .slice(0, 8);
    
    const jobs = jobSections.map(section => {
      const titleEl = section.querySelector('h3 a, [data-test="job-tile-title-link"], h2 a');
      const title = titleEl ? titleEl.textContent.trim() : '';
      const href = titleEl ? titleEl.href : '';
      
      // Get full text and parse details
      const text = section.textContent;
      
      // Extract budget/rate
      const budgetMatch = text.match(/Budget:\\s*\\$([\\d,]+)/i) || text.match(/Est\\.\\s*Budget:\\s*\\$([\\d,]+)/i);
      const hourlyMatch = text.match(/Hourly:\\s*\\$(\\d+)-\\$(\\d+)/i);
      const budget = budgetMatch ? '$' + budgetMatch[1] : hourlyMatch ? '$' + hourlyMatch[1] + '-$' + hourlyMatch[2] + '/hr' : '';
      
      // Extract level
      const levelMatch = text.match(/(Entry level|Intermediate|Expert)/i);
      const level = levelMatch ? levelMatch[1] : '';
      
      // Extract type
      const isFixed = text.includes('Fixed-price');
      const isHourly = text.includes('Hourly');
      
      // Extract proposals count
      const proposalMatch = text.match(/Proposals:\\s*([\\w\\s]+?)(?=\\n|$)/i);
      const proposals = proposalMatch ? proposalMatch[1].trim() : '';
      
      // Extract time posted
      const timeMatch = text.match(/Posted\\s+(\\d+\\s+\\w+\\s+ago|yesterday|just now)/i);
      const posted = timeMatch ? timeMatch[1] : '';
      
      // Get description snippet
      const descStart = text.indexOf(level) + level.length;
      const skillsStart = text.indexOf('Skills');
      let desc = '';
      if (skillsStart > descStart && descStart > 0) {
        desc = text.substring(descStart, skillsStart).trim().substring(0, 200);
      }
      
      // Extract payment info
      const payVerified = text.includes('Payment verified');
      const spentMatch = text.match(/\\$(\\d+[KM]?\\+?)\\s*spent/i);
      const spent = spentMatch ? '$' + spentMatch[1] + ' spent' : '';
      
      return {
        title: title.substring(0, 80),
        href,
        type: isFixed ? 'Fixed' : isHourly ? 'Hourly' : '',
        budget,
        level,
        posted,
        proposals,
        payVerified,
        spent,
        desc: desc.substring(0, 150)
      };
    });
    
    return JSON.stringify(jobs, null, 2);
  `);

  return { ws, send, eval_, jobs: JSON.parse(r) };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("upwork.com");
  console.log("Connected\n");

  const searches = [
    'data entry',
    'content writing',
    'proofreading editing',
    'virtual assistant',
    'resume writing',
    'document formatting'
  ];

  const allJobs = [];

  for (const query of searches) {
    const result = await searchJobs(ws, send, eval_, query);
    ws = result.ws; send = result.send; eval_ = result.eval_;
    
    console.log(`\n=== ${query.toUpperCase()} ===`);
    const validJobs = result.jobs.filter(j => j.title.length > 0);
    validJobs.forEach((j, i) => {
      console.log(`${i+1}. ${j.title}`);
      console.log(`   ${j.type} ${j.budget} | ${j.level} | Posted: ${j.posted} | Proposals: ${j.proposals}`);
      if (j.spent) console.log(`   Client: ${j.payVerified ? 'Verified' : ''} ${j.spent}`);
      if (j.desc) console.log(`   ${j.desc.substring(0, 120)}`);
      console.log('');
    });
    allJobs.push(...validJobs.map(j => ({ ...j, category: query })));
  }

  console.log("\n\n========================================");
  console.log("SUMMARY: Best quick jobs to apply for");
  console.log("========================================\n");
  
  // Filter for jobs with good potential
  const good = allJobs.filter(j => j.title.length > 5);
  good.slice(0, 20).forEach((j, i) => {
    console.log(`${i+1}. [${j.category}] ${j.title}`);
    console.log(`   ${j.type} ${j.budget} | ${j.level}`);
    console.log('');
  });

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
