// Playwright CDP script - scrape Upwork, Fiverr, and freelance platforms
import { chromium } from 'playwright';

const CDP_URL = 'http://localhost:9222';

async function main() {
  console.log('Connecting to Chrome via CDP...');
  const browser = await chromium.connectOverCDP(CDP_URL);
  const contexts = browser.contexts();
  const context = contexts[0] || await browser.newContext();

  // Get existing pages
  const pages = context.pages();
  console.log(`Found ${pages.length} existing tab(s)`);

  // Check if we're logged into Upwork
  let upworkPage = pages.find(p => p.url().includes('upwork.com'));
  if (!upworkPage) {
    upworkPage = await context.newPage();
    await upworkPage.goto('https://www.upwork.com/nx/find-work/best-matches', { waitUntil: 'domcontentloaded', timeout: 15000 });
  }

  await new Promise(r => setTimeout(r, 3000));
  const upworkUrl = upworkPage.url();
  console.log(`\nUpwork URL: ${upworkUrl}`);

  if (upworkUrl.includes('login') || upworkUrl.includes('account-security')) {
    console.log('\n⚠️  UPWORK: Not logged in. Please log in on the CDP Chrome window.');
    console.log('Waiting 60 seconds for login...');

    // Wait for navigation away from login page
    try {
      await upworkPage.waitForURL('**/find-work/**', { timeout: 60000 });
      console.log('✓ Upwork login successful!');
      await new Promise(r => setTimeout(r, 3000));
    } catch {
      console.log('⏱ Login timeout - checking current state...');
      if (upworkPage.url().includes('login')) {
        console.log('Still on login page. Skipping Upwork scrape.');
        console.log(JSON.stringify({ platform: 'upwork', status: 'needs_login' }));
      }
    }
  }

  // Scrape Upwork jobs if logged in
  if (!upworkPage.url().includes('login')) {
    console.log('\n--- UPWORK JOBS ---');

    // Check connects balance first
    try {
      await upworkPage.goto('https://www.upwork.com/nx/find-work/best-matches', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await new Promise(r => setTimeout(r, 3000));

      const connectsInfo = await upworkPage.evaluate(() => {
        const el = document.querySelector('[data-test="connects-amount"], .connects-amount, [class*="connect"]');
        return el ? el.textContent.trim() : 'Could not find connects count on page';
      });
      console.log(`Connects: ${connectsInfo}`);

      // Scrape job listings
      const jobs = await upworkPage.evaluate(() => {
        const jobCards = document.querySelectorAll('[data-test="job-tile"], .job-tile, section.up-card-section, [class*="JobTile"], article');
        const results = [];
        jobCards.forEach((card, i) => {
          if (i >= 15) return;
          const title = card.querySelector('h2, h3, [class*="title"] a, a[class*="Title"]')?.textContent?.trim() || '';
          const budget = card.querySelector('[data-test="budget"], [class*="budget"], [class*="Budget"]')?.textContent?.trim() || '';
          const posted = card.querySelector('[data-test="posted-on"], [class*="posted"], time, [class*="Posted"]')?.textContent?.trim() || '';
          const skills = Array.from(card.querySelectorAll('[data-test="token"], .up-skill-badge, [class*="skill"], [class*="Skill"] span')).map(s => s.textContent.trim()).filter(Boolean).slice(0, 5);
          const desc = card.querySelector('[data-test="description"], [class*="description"], p')?.textContent?.trim()?.substring(0, 200) || '';
          const link = card.querySelector('a[href*="/jobs/"]')?.href || '';
          if (title) results.push({ title, budget, posted, skills: skills.join(', '), desc, link });
        });
        return results;
      });

      if (jobs.length === 0) {
        // Try getting page content for debugging
        const bodyText = await upworkPage.evaluate(() => document.body.innerText.substring(0, 2000));
        console.log('No job cards found. Page content preview:');
        console.log(bodyText);
      } else {
        jobs.forEach((job, i) => {
          console.log(`\n${i + 1}. ${job.title}`);
          if (job.budget) console.log(`   Budget: ${job.budget}`);
          if (job.posted) console.log(`   Posted: ${job.posted}`);
          if (job.skills) console.log(`   Skills: ${job.skills}`);
          if (job.desc) console.log(`   ${job.desc}`);
          if (job.link) console.log(`   Link: ${job.link}`);
        });
      }
    } catch (e) {
      console.log('Error scraping Upwork:', e.message);
    }

    // Also search for Revit/BIM specific jobs
    console.log('\n\n--- UPWORK REVIT/BIM JOBS ---');
    try {
      await upworkPage.goto('https://www.upwork.com/nx/search/jobs/?q=revit+BIM&sort=recency&payment_verified=1', { waitUntil: 'domcontentloaded', timeout: 15000 });
      await new Promise(r => setTimeout(r, 3000));

      const bimJobs = await upworkPage.evaluate(() => {
        const jobCards = document.querySelectorAll('[data-test="job-tile"], .job-tile, section.up-card-section, [class*="JobTile"], article');
        const results = [];
        jobCards.forEach((card, i) => {
          if (i >= 10) return;
          const title = card.querySelector('h2, h3, [class*="title"] a, a[class*="Title"]')?.textContent?.trim() || '';
          const budget = card.querySelector('[data-test="budget"], [class*="budget"], [class*="Budget"]')?.textContent?.trim() || '';
          const posted = card.querySelector('[data-test="posted-on"], [class*="posted"], time, [class*="Posted"]')?.textContent?.trim() || '';
          const desc = card.querySelector('[data-test="description"], [class*="description"], p')?.textContent?.trim()?.substring(0, 200) || '';
          const link = card.querySelector('a[href*="/jobs/"]')?.href || '';
          if (title) results.push({ title, budget, posted, desc, link });
        });
        return results;
      });

      bimJobs.forEach((job, i) => {
        console.log(`\n${i + 1}. ${job.title}`);
        if (job.budget) console.log(`   Budget: ${job.budget}`);
        if (job.posted) console.log(`   Posted: ${job.posted}`);
        if (job.desc) console.log(`   ${job.desc}`);
      });
    } catch (e) {
      console.log('Error searching BIM jobs:', e.message);
    }
  }

  // Open Fiverr
  console.log('\n\n--- FIVERR ---');
  let fiverrPage = pages.find(p => p.url().includes('fiverr.com'));
  if (!fiverrPage) {
    fiverrPage = await context.newPage();
  }
  await fiverrPage.goto('https://www.fiverr.com/users/weberg619/manage_gigs', { waitUntil: 'domcontentloaded', timeout: 15000 });
  await new Promise(r => setTimeout(r, 3000));

  const fiverrUrl = fiverrPage.url();
  if (fiverrUrl.includes('login') || fiverrUrl.includes('join')) {
    console.log('⚠️  FIVERR: Not logged in. Please log in on the CDP Chrome.');
  } else {
    const fiverrData = await fiverrPage.evaluate(() => {
      return {
        url: location.href,
        pageText: document.body.innerText.substring(0, 3000)
      };
    });
    console.log(`URL: ${fiverrData.url}`);
    console.log(fiverrData.pageText);
  }

  // Also check Fiverr buyer requests / briefs
  console.log('\n\n--- FIVERR BRIEFS ---');
  try {
    await fiverrPage.goto('https://www.fiverr.com/users/weberg619/briefs', { waitUntil: 'domcontentloaded', timeout: 15000 });
    await new Promise(r => setTimeout(r, 3000));

    const briefsData = await fiverrPage.evaluate(() => {
      return document.body.innerText.substring(0, 2000);
    });
    console.log(briefsData);
  } catch (e) {
    console.log('Error checking briefs:', e.message);
  }

  console.log('\n\n--- DONE ---');
  // Don't close browser - keep it open for user
  process.exit(0);
}

main().catch(e => { console.error('Fatal:', e.message); process.exit(1); });
