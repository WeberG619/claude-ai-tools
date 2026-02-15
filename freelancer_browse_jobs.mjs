// Browse and bid on top Freelancer jobs
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

const TOP_JOBS = [
  { title: "Excel Numerical Data Cleanup", budget: 526, url: "https://www.freelancer.com/projects/data-analysis/excel-numerical-data-cleanup-40214417" },
  { title: "Excel Text Data Cleanup", budget: 370, url: "https://www.freelancer.com/projects/excel-vba/excel-text-data-cleanup" },
  { title: "Dissertation Proofreading Needed", budget: 329, url: "https://www.freelancer.com/projects/academic-writing/dissertation-proofreading-needed" },
  { title: "Classic Website Copywriting & Editing", budget: 234, url: "https://www.freelancer.com/projects/creative-writing/classic-website-copywriting-editing" },
  { title: "Excel/CSV Database Entry Support", budget: 0, url: "https://www.freelancer.com/projects/data-cleansing/excel-csv-database-entry-support" },
];

async function main() {
  const { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  const jobDetails = [];

  for (const job of TOP_JOBS) {
    console.log(`\n=== ${job.title} ($${job.budget}) ===`);

    // Navigate to job page
    await eval_(`window.location.href = ${JSON.stringify(job.url)}; return 'ok';`);
    await sleep(5000);

    // Read job details
    const r = await eval_(`
      return new Promise((resolve) => {
        setTimeout(() => {
          const bodyText = document.body?.innerText || '';

          // Extract description - look for project description area
          let desc = '';
          const descEl = document.querySelector('.ProjectDescription, [class*="ProjectDescription"], .project-details, [class*="project-detail"]');
          if (descEl) desc = descEl.textContent.trim();

          // Parse key info from body text
          const lines = bodyText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

          // Find budget line
          const budgetLine = lines.find(l => l.includes('Budget') || l.includes('$'));

          // Find bids count
          const bidsLine = lines.find(l => l.includes('bid') || l.includes('Bid'));

          // Find skills
          const skillsEl = document.querySelectorAll('[class*="SkillTag"], [class*="skill-tag"], .PageProjectViewLogout-detail-tags a, a[href*="/jobs/"]');
          const skills = Array.from(skillsEl).map(el => el.textContent.trim()).filter(t => t.length > 1 && t.length < 30).slice(0, 10);

          // Get the important part of the page
          const important = bodyText.substring(0, 3000);

          resolve(JSON.stringify({
            url: location.href,
            title: document.querySelector('h1')?.textContent?.trim() || '',
            desc: desc.substring(0, 800),
            budget: budgetLine || '',
            bids: bidsLine || '',
            skills,
            preview: important
          }));
        }, 2000);
      });
    `);

    try {
      const details = JSON.parse(r);
      console.log("Title:", details.title);
      console.log("URL:", details.url);
      console.log("Skills:", details.skills.join(", "));
      console.log("Preview:", details.preview.substring(0, 500));
      jobDetails.push(details);
    } catch (e) {
      console.log("Raw:", r?.substring(0, 500));
    }
  }

  console.log("\n\n=== SUMMARY ===");
  jobDetails.forEach((j, i) => {
    console.log(`\n${i+1}. ${j.title || TOP_JOBS[i].title}`);
    console.log(`   URL: ${j.url}`);
    console.log(`   Skills: ${j.skills?.join(", ")}`);
  });

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
