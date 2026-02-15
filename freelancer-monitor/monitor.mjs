#!/usr/bin/env node
// Freelancer.com Job Monitor Daemon
// Runs 24/7, polls for new jobs, checks bid responses, alerts via voice TTS
// Usage: node monitor.mjs [--interval 300] [--voice]

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';
import { execSync, exec } from 'child_process';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const CDP_HTTP = "http://localhost:9222";
const sleep = ms => new Promise(r => setTimeout(r, ms));

// Configuration
const CONFIG = {
  pollIntervalSec: parseInt(process.argv.find((a, i) => process.argv[i - 1] === '--interval') || '300'), // 5 min default
  voiceAlerts: process.argv.includes('--voice'),
  dataDir: path.join(__dirname, 'data'),
  logFile: path.join(__dirname, 'data', 'monitor.log'),
  jobsFile: path.join(__dirname, 'data', 'seen_jobs.json'),
  alertsFile: path.join(__dirname, 'data', 'alerts.json'),
  bidsFile: path.join(__dirname, 'data', 'active_bids.json'),

  // Job search categories (things Claude can do)
  searchCategories: [
    'data-entry', 'article-writing', 'research-writing', 'excel',
    'copywriting', 'transcription', 'data-processing', 'technical-writing',
    'proofreading', 'content-writing', 'typing', 'data-cleansing',
    'editing', 'blog-writing'
  ],

  // Keywords that indicate jobs Claude can handle well
  goodKeywords: [
    'data entry', 'typing', 'excel', 'spreadsheet', 'transcription',
    'article', 'blog', 'content writing', 'copywriting', 'research',
    'proofreading', 'editing', 'summary', 'report writing', 'documentation',
    'csv', 'database entry', 'web research', 'list building', 'lead generation',
    'pdf to excel', 'data extraction', 'data mining', 'rewriting'
  ],

  // Keywords that indicate jobs Claude can NOT do
  badKeywords: [
    'phone call', 'video call', 'live chat', 'in person', 'on site',
    'social media management', 'photography', 'video editing', 'voice over',
    'cold calling', 'telemarketing', 'physical', 'local only'
  ],

  // Budget thresholds (USD)
  minBudgetUSD: 20,
  maxBidsToCompete: 50
};

// Ensure data directory exists
if (!fs.existsSync(CONFIG.dataDir)) fs.mkdirSync(CONFIG.dataDir, { recursive: true });

// Logging
function log(msg, level = 'INFO') {
  const ts = new Date().toISOString();
  const line = `[${ts}] [${level}] ${msg}`;
  console.log(line);
  try {
    fs.appendFileSync(CONFIG.logFile, line + '\n');
  } catch (e) {}
}

// Voice alert
function speak(text) {
  if (!CONFIG.voiceAlerts) return;
  try {
    exec(`python3 /mnt/d/_CLAUDE-TOOLS/voice-mcp/speak.py "${text.replace(/"/g, "'")}"`, { timeout: 10000 });
  } catch (e) {
    log(`Voice alert failed: ${e.message}`, 'WARN');
  }
}

// Load/save JSON
function loadJSON(file, defaultVal = {}) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (e) {
    return defaultVal;
  }
}

function saveJSON(file, data) {
  fs.writeFileSync(file, JSON.stringify(data, null, 2));
}

// CDP connection
async function connectToFreelancer() {
  try {
    const tabsRes = await fetch(`${CDP_HTTP}/json`);
    const tabs = await tabsRes.json();
    const tab = tabs.find(t => t.type === "page" && t.url.includes("freelancer.com"));
    if (!tab) return null;

    const ws = new WebSocket(tab.webSocketDebuggerUrl);
    await new Promise((res, rej) => {
      ws.addEventListener("open", res);
      ws.addEventListener("error", rej);
      setTimeout(() => rej(new Error("timeout")), 5000);
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
        expression: `(() => { ${expr} })()`,
        returnByValue: true, awaitPromise: true
      });
      if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails));
      return r.result?.value;
    };

    return { ws, send, eval_ };
  } catch (e) {
    return null;
  }
}

// Score a job for how well Claude can handle it
function scoreJob(job) {
  let score = 0;
  const text = `${job.title} ${job.desc || ''} ${job.skills || ''}`.toLowerCase();

  // Good keyword matches
  for (const kw of CONFIG.goodKeywords) {
    if (text.includes(kw)) score += 10;
  }

  // Bad keyword matches
  for (const kw of CONFIG.badKeywords) {
    if (text.includes(kw)) score -= 50;
  }

  // Budget bonus (higher budget = more interesting)
  if (job.budgetUSD && job.budgetUSD > 100) score += 5;
  if (job.budgetUSD && job.budgetUSD > 300) score += 10;

  // Low competition bonus
  if (job.bidCount && job.bidCount < 10) score += 15;
  if (job.bidCount && job.bidCount < 5) score += 10;

  // Penalty for too many bids
  if (job.bidCount && job.bidCount > CONFIG.maxBidsToCompete) score -= 20;

  return score;
}

// Check for new jobs in a category
async function searchJobs(conn, category) {
  const url = `https://www.freelancer.com/jobs/${category}/`;
  await conn.send("Page.navigate", { url });
  await sleep(4000);

  const r = await conn.eval_(`
    const links = Array.from(document.querySelectorAll('a'))
      .filter(a => {
        const h = a.href || '';
        return h.includes('/projects/') && !h.includes('/proposals') &&
               !h.includes('/payments') && !h.includes('/reviews') &&
               a.textContent.trim().length > 10 && a.textContent.trim().length < 150;
      });
    const jobs = [];
    const seen = new Set();
    for (const link of links) {
      const title = link.textContent.trim();
      if (seen.has(title) || title.length < 10) continue;
      seen.add(title);
      let container = link;
      for (let i = 0; i < 8; i++) {
        container = container.parentElement;
        if (!container) break;
        const rect = container.getBoundingClientRect();
        if (rect.height > 80 && rect.height < 500 && rect.width > 400) break;
      }
      if (!container) continue;
      const cardText = container.innerText || '';
      const budgetMatch = cardText.match(/([\$\\u20B9\\u20AC\\u00A3][\\d,]+)/);
      const bidMatch = cardText.match(/(\\d+)\\s*(?:bids?|entries|proposals)/i);
      const desc = cardText.split('\\n')
        .filter(l => l.trim() !== title && l.trim().length > 30 && l.trim().length < 300)
        .slice(0, 1).join(' ').substring(0, 200);
      jobs.push({ title, href: link.href, budget: budgetMatch ? budgetMatch[1] : '', bids: bidMatch ? bidMatch[1] + ' bids' : '', desc, skills: '' });
    }
    return JSON.stringify(jobs.slice(0, 15));
  `);

  try {
    return JSON.parse(r);
  } catch (e) {
    return [];
  }
}

// Check for bid responses / messages / notifications
async function checkNotifications(conn) {
  await conn.send("Page.navigate", { url: "https://www.freelancer.com/dashboard" });
  await sleep(3000);

  const r = await conn.eval_(`
    // Check notification count
    const notifBadge = document.querySelector('[class*="notification" i] [class*="badge" i], [class*="NotificationBadge" i]');
    const notifCount = notifBadge ? parseInt(notifBadge.textContent) || 0 : 0;

    // Check messages
    const msgBadge = document.querySelector('[class*="message" i] [class*="badge" i], [class*="MessageBadge" i]');
    const msgCount = msgBadge ? parseInt(msgBadge.textContent) || 0 : 0;

    // Check for awarded projects
    const awarded = document.body.innerText.includes('has been awarded') ||
                    document.body.innerText.includes('You have been awarded') ||
                    document.body.innerText.includes('project awarded');

    // Check for new messages about bids
    const bidMessages = Array.from(document.querySelectorAll('[class*="notification" i], [class*="Notification" i]'))
      .filter(el => el.offsetParent !== null)
      .map(el => el.textContent.trim().substring(0, 100))
      .filter(t => t.length > 10);

    return JSON.stringify({
      notifCount,
      msgCount,
      awarded,
      bidMessages: bidMessages.slice(0, 5),
      preview: document.body.innerText.substring(0, 500)
    });
  `);

  try {
    return JSON.parse(r);
  } catch (e) {
    return { notifCount: 0, msgCount: 0, awarded: false, bidMessages: [] };
  }
}

// Main monitoring loop
async function monitorLoop() {
  log('=== Freelancer Monitor Starting ===');
  log(`Poll interval: ${CONFIG.pollIntervalSec}s | Voice: ${CONFIG.voiceAlerts}`);
  log(`Searching ${CONFIG.searchCategories.length} categories`);

  const seenJobs = loadJSON(CONFIG.jobsFile, { seen: {}, newJobs: [] });
  const alerts = loadJSON(CONFIG.alertsFile, { alerts: [] });

  let cycleNum = 0;

  while (true) {
    cycleNum++;
    log(`\n--- Cycle ${cycleNum} ---`);

    const conn = await connectToFreelancer();
    if (!conn) {
      log('Cannot connect to Freelancer tab. Chrome/CDP not available.', 'WARN');
      log(`Retrying in ${CONFIG.pollIntervalSec}s...`);
      await sleep(CONFIG.pollIntervalSec * 1000);
      continue;
    }

    try {
      // 1. Check notifications/messages
      log('Checking notifications...');
      const notifs = await checkNotifications(conn);
      if (notifs.msgCount > 0) {
        const alert = { type: 'message', count: notifs.msgCount, time: new Date().toISOString() };
        alerts.alerts.push(alert);
        log(`NEW MESSAGES: ${notifs.msgCount}`, 'ALERT');
        speak(`Weber, you have ${notifs.msgCount} new messages on Freelancer`);
      }
      if (notifs.awarded) {
        const alert = { type: 'awarded', time: new Date().toISOString() };
        alerts.alerts.push(alert);
        log('PROJECT AWARDED!', 'ALERT');
        speak('Weber! You have been awarded a project on Freelancer!');
      }
      if (notifs.notifCount > 0) {
        log(`Notifications: ${notifs.notifCount}`);
      }

      // 2. Search for new jobs (rotate through categories - 2 per cycle)
      const catIndex = ((cycleNum - 1) * 2) % CONFIG.searchCategories.length;
      const categoriesToSearch = [
        CONFIG.searchCategories[catIndex],
        CONFIG.searchCategories[(catIndex + 1) % CONFIG.searchCategories.length]
      ];

      let newJobsThisCycle = [];

      for (const cat of categoriesToSearch) {
        log(`Searching: ${cat}`);
        const jobs = await searchJobs(conn, cat);
        log(`  Found ${jobs.length} listings`);

        for (const job of jobs) {
          const jobKey = job.href || job.title;
          if (!seenJobs.seen[jobKey]) {
            seenJobs.seen[jobKey] = { firstSeen: new Date().toISOString(), category: cat };

            // Parse budget
            const budgetMatch = job.budget.match(/[\$₹€£]?([\d,]+)/);
            const budgetNum = budgetMatch ? parseInt(budgetMatch[1].replace(/,/g, '')) : 0;
            const isINR = job.budget.includes('INR') || job.budget.includes('₹');
            job.budgetUSD = isINR ? Math.round(budgetNum / 83) : budgetNum;

            // Parse bid count
            const bidMatch = job.bids.match(/(\d+)/);
            job.bidCount = bidMatch ? parseInt(bidMatch[1]) : 0;

            // Score it
            job.score = scoreJob(job);
            job.category = cat;

            if (job.score > 0) {
              newJobsThisCycle.push(job);
              seenJobs.newJobs.push(job);
              log(`  NEW: "${job.title}" | $${job.budgetUSD} | ${job.bidCount} bids | Score: ${job.score}`);
            }
          }
        }
      }

      // Alert on high-quality new jobs
      const hotJobs = newJobsThisCycle.filter(j => j.score >= 20);
      if (hotJobs.length > 0) {
        log(`${hotJobs.length} HOT NEW JOBS found!`, 'ALERT');
        for (const job of hotJobs) {
          log(`  HOT: "${job.title}" | $${job.budgetUSD} | Score: ${job.score}`, 'ALERT');
        }
        speak(`Weber, ${hotJobs.length} new matching jobs found on Freelancer. ${hotJobs[0].title.substring(0, 50)}`);

        // Save alert
        alerts.alerts.push({
          type: 'new_jobs',
          count: hotJobs.length,
          jobs: hotJobs.map(j => ({ title: j.title, budget: j.budgetUSD, score: j.score, href: j.href })),
          time: new Date().toISOString()
        });
      }

      // Save state
      saveJSON(CONFIG.jobsFile, seenJobs);
      saveJSON(CONFIG.alertsFile, alerts);

      // Stats
      const totalSeen = Object.keys(seenJobs.seen).length;
      const totalNew = seenJobs.newJobs.length;
      log(`Stats: ${totalSeen} total seen | ${totalNew} matching jobs tracked | ${alerts.alerts.length} alerts`);

    } catch (e) {
      log(`Error in cycle: ${e.message}`, 'ERROR');
    } finally {
      try { conn.ws.close(); } catch (e) {}
    }

    // Navigate back to dashboard so it's ready for next check
    log(`Next check in ${CONFIG.pollIntervalSec}s`);
    await sleep(CONFIG.pollIntervalSec * 1000);
  }
}

// Status command - read current state
if (process.argv.includes('--status')) {
  const seenJobs = loadJSON(CONFIG.jobsFile, { seen: {}, newJobs: [] });
  const alerts = loadJSON(CONFIG.alertsFile, { alerts: [] });
  console.log('\n=== Freelancer Monitor Status ===');
  console.log(`Jobs tracked: ${Object.keys(seenJobs.seen).length}`);
  console.log(`Matching jobs: ${seenJobs.newJobs.length}`);
  console.log(`Alerts: ${alerts.alerts.length}`);
  console.log('\nTop matching jobs:');
  seenJobs.newJobs
    .sort((a, b) => (b.score || 0) - (a.score || 0))
    .slice(0, 10)
    .forEach((j, i) => {
      console.log(`  ${i + 1}. [Score ${j.score}] "${j.title}" | $${j.budgetUSD} | ${j.bidCount} bids`);
    });
  console.log('\nRecent alerts:');
  alerts.alerts.slice(-5).forEach(a => {
    console.log(`  [${a.time}] ${a.type}: ${a.count || ''} ${a.type === 'new_jobs' ? a.jobs?.map(j => j.title).join(', ') : ''}`);
  });
  process.exit(0);
}

// Run the monitor
monitorLoop().catch(e => {
  log(`Fatal error: ${e.message}`, 'FATAL');
  process.exit(1);
});
