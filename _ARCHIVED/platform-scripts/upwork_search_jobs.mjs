// Search for matching jobs across multiple queries and collect details
const CDP = 'http://localhost:9222';
const sleep = ms => new Promise(r => setTimeout(r, ms));
import { writeFileSync } from 'fs';

async function getPages() {
  const r = await fetch(`${CDP}/json`);
  return (await r.json()).filter(t => t.type === 'page');
}

function connect(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let id = 1;
    const pending = new Map();
    ws.addEventListener('message', e => {
      const msg = JSON.parse(e.data);
      if (msg.id && pending.has(msg.id)) {
        const p = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? p.rej(new Error(msg.error.message)) : p.res(msg.result);
      }
    });
    const send = (method, params = {}) => new Promise((res, rej) => {
      const mid = id++;
      pending.set(mid, { res, rej });
      ws.send(JSON.stringify({ id: mid, method, params }));
    });
    const ev = async (expr) => {
      const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };
    ws.addEventListener('open', () => resolve({ ws, send, ev, close: () => ws.close() }));
    ws.addEventListener('error', reject);
  });
}

async function searchJobs(c, query) {
  console.log(`\n--- Searching: "${query}" ---`);
  await c.ev(`window.location.href = 'https://www.upwork.com/nx/search/jobs/?q=${encodeURIComponent(query)}&sort=recency'`);
  await sleep(4000);

  const jobs = await c.ev(`
    (() => {
      // Get all job tile sections
      var sections = document.querySelectorAll('article, [data-test="UpCJobTile"], section[data-ev-label*="job_tile"]');
      if (sections.length === 0) {
        // Broader search
        var main = document.querySelector('main') || document.body;
        sections = main.querySelectorAll('section');
      }

      var result = [];
      for (var i = 0; i < Math.min(sections.length, 8); i++) {
        var s = sections[i];
        // Find title link
        var titleLink = s.querySelector('a[href*="/jobs/"]');
        if (!titleLink) continue;

        var title = titleLink.textContent.trim();
        var href = titleLink.href;

        // Description
        var allText = s.innerText;

        // Budget - look for dollar amounts
        var budgetMatch = allText.match(/\\$([\d,]+(?:\\.\\d{2})?)/);
        var budget = budgetMatch ? '$' + budgetMatch[1] : '';

        // Hourly rate
        if (!budget) {
          var hourlyMatch = allText.match(/\\$([\d.]+)\\s*-\\s*\\$([\d.]+)/);
          if (hourlyMatch) budget = '$' + hourlyMatch[1] + '-$' + hourlyMatch[2] + '/hr';
        }

        // Fixed price
        var fixedMatch = allText.match(/Fixed-price/i);
        var hourlyType = allText.match(/Hourly/i);
        var type = fixedMatch ? 'Fixed' : (hourlyType ? 'Hourly' : '');

        // Posted time
        var timeMatch = allText.match(/(\\d+\\s*(minute|hour|day|week)s?\\s*ago|yesterday|just now)/i);
        var posted = timeMatch ? timeMatch[0] : '';

        // Proposals count
        var propMatch = allText.match(/(\\d+)\\s*to\\s*(\\d+)\\s*proposals/i) || allText.match(/Less than (\\d+) proposals/i);
        var proposals = propMatch ? propMatch[0] : '';

        // Skills
        var skillEls = s.querySelectorAll('.air3-token, [class*="skill"] span, [class*="tag"]');
        var skills = [];
        for (var j = 0; j < skillEls.length; j++) {
          var st = skillEls[j].textContent.trim();
          if (st.length > 1 && st.length < 40 && !st.includes('$')) skills.push(st);
        }

        if (title.length > 5) {
          result.push({
            title: title.substring(0, 120),
            href: href,
            budget: budget,
            type: type,
            posted: posted,
            proposals: proposals,
            skills: skills.slice(0, 8).join(', '),
            excerpt: allText.substring(0, 300)
          });
        }
      }
      return JSON.stringify(result);
    })()
  `);

  return JSON.parse(jobs || '[]');
}

async function main() {
  const pages = await getPages();
  const tab = pages.find(p => p.url.includes('upwork.com'));
  if (!tab) { console.log('No Upwork tab found'); process.exit(1); }
  const c = await connect(tab.webSocketDebuggerUrl);

  const searches = [
    'revit plugin C#',
    'revit API add-in',
    'BIM automation developer',
    'C# WPF desktop application',
    'AutoCAD plugin development',
    '.NET automation tool',
    'dynamo revit script',
    'C# developer small project',
    'Windows desktop app C#',
    'Python automation script'
  ];

  const allJobs = [];
  const seenHrefs = new Set();

  for (const query of searches) {
    try {
      const jobs = await searchJobs(c, query);
      let newCount = 0;
      for (const job of jobs) {
        if (!seenHrefs.has(job.href) && job.title) {
          seenHrefs.add(job.href);
          allJobs.push({ ...job, searchQuery: query });
          newCount++;
        }
      }
      console.log(`  Found ${jobs.length} results, ${newCount} new unique`);
    } catch (e) {
      console.log(`  Error: ${e.message}`);
    }
  }

  // Sort by most recent
  console.log(`\n========================================`);
  console.log(`TOTAL UNIQUE JOBS FOUND: ${allJobs.length}`);
  console.log(`========================================\n`);

  for (let i = 0; i < allJobs.length; i++) {
    const j = allJobs[i];
    console.log(`${i + 1}. [${j.budget || j.type || 'N/A'}] ${j.title}`);
    console.log(`   Posted: ${j.posted || 'N/A'} | Proposals: ${j.proposals || 'N/A'}`);
    console.log(`   Skills: ${j.skills || 'N/A'}`);
    console.log('');
  }

  // Save to file
  writeFileSync('D:\\_CLAUDE-TOOLS\\upwork_jobs.json', JSON.stringify(allJobs, null, 2));
  console.log('Saved to upwork_jobs.json');

  c.close();
  process.exit(0);
}

main().catch(e => { console.error('Error:', e.message); process.exit(1); });
