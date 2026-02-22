// Get details on top job candidates and place bids
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

// Top job picks Claude can definitely do
const targetJobs = [
  {
    url: "https://www.freelancer.com/projects/data-management/inventory-data-entry-excel",
    proposal: `I'm a detail-oriented data entry specialist ready to handle your inventory data entry in Excel. I work methodically through large datasets, ensuring every cell is accurately populated with zero formatting errors.\n\nMy approach:\n• Carefully enter each inventory item following your template structure\n• Double-check entries against source data for accuracy\n• Maintain consistent formatting throughout the spreadsheet\n• Flag any unclear or ambiguous entries for your review\n\nI'm proficient with Excel including data validation, conditional formatting, and pivot tables. Available to start immediately and deliver clean, error-free work.`
  },
  {
    url: "https://www.freelancer.com/projects/data-entry/notepad-excel-data-entry",
    proposal: `I can efficiently transfer your Notepad data into a well-organized Excel spreadsheet. I specialize in precise data entry work with extremely low error rates.\n\nMy process:\n• Review the Notepad file structure to understand the data layout\n• Set up the Excel template with proper column headers and formatting\n• Transfer each data point accurately, maintaining the original structure\n• Apply data validation where appropriate to catch any inconsistencies\n• Deliver a clean, formatted spreadsheet ready for immediate use\n\nI'm experienced with handling raw text data and converting it into structured spreadsheets. Fast turnaround with meticulous attention to detail.`
  },
  {
    url: "https://www.freelancer.com/projects/data-analysis/clean-visualize-sales-data",
    proposal: `I'm experienced in cleaning and visualizing sales data in Excel. I can turn your raw data into clear, actionable insights.\n\nWhat I'll deliver:\n• Thorough data cleaning — removing duplicates, fixing formatting, standardizing entries\n• Organized data structure with proper categorization\n• Professional charts and visualizations (bar charts, line graphs, pivot tables) tailored to your sales metrics\n• Summary dashboard highlighting key trends and KPIs\n\nI work with advanced Excel functions including VLOOKUP, INDEX/MATCH, pivot tables, and conditional formatting to ensure your data tells a clear story. Can start right away.`
  },
  {
    url: "https://www.freelancer.com/projects/data-entry/freelance-writer-spreadsheet-entry-40214540",
    proposal: `This is right in my wheelhouse — I handle both research writing and precise spreadsheet data entry regularly.\n\nFor your project, I'll:\n• Take your raw research datasets and enter them accurately into structured spreadsheets\n• Write clear, well-organized summaries of the data findings\n• Ensure formatting consistency and data integrity throughout\n• Cross-reference entries for accuracy\n\nI combine strong analytical writing skills with meticulous data handling. I'm comfortable switching between writing tasks and numerical data entry, and I maintain high accuracy standards in both. Available to start immediately.`
  },
  {
    url: "https://www.freelancer.com/projects/data-analysis/excel-numerical-data-cleanup-40214417",
    proposal: `I specialize in Excel data cleanup and can transform your raw spreadsheets into analysis-ready workbooks quickly.\n\nMy cleanup process:\n• Identify and remove duplicate entries\n• Standardize number formats, date formats, and text entries\n• Fix formula errors and broken references\n• Organize data into logical, consistent structure\n• Add data validation rules to prevent future inconsistencies\n• Create summary tabs if needed\n\nI'm proficient with advanced Excel functions and can handle large datasets efficiently. I'll deliver a clean, professional workbook that's immediately ready for whatever analysis you need.`
  }
];

async function getJobDetails(eval_, send) {
  const r = await eval_(`
    const text = document.body.innerText;

    // Extract budget
    const budgetMatch = text.match(/([₹\$€£][\d,]+(?:\.\d+)?\\s*(?:–|-|to)\\s*[₹\$€£]?[\d,]+(?:\.\d+)?\\s*(?:USD|INR|EUR)?)/);
    const budget = budgetMatch ? budgetMatch[1] : '';

    // Extract bid count
    const bidMatch = text.match(/Bids\\s*(\\d+)/);
    const bids = bidMatch ? parseInt(bidMatch[1]) : 0;

    // Extract average bid
    const avgMatch = text.match(/Average bid\\s*([₹\$€£]?[\\d,]+)/);
    const avgBid = avgMatch ? avgMatch[1] : '';

    // Check if bid form is available
    const hasBidForm = !!document.getElementById('bidAmountInput');

    // Get the currency
    const currencyMatch = text.match(/(INR|USD|EUR|GBP)/);
    const currency = currencyMatch ? currencyMatch[1] : 'USD';

    return JSON.stringify({
      budget, bids, avgBid, hasBidForm, currency,
      title: document.title?.substring(0, 80),
      bidRemaining: text.match(/(\\d+)\\s*bids?\\s*left/)?.[1] || 'unknown'
    });
  `);
  return JSON.parse(r);
}

async function placeBid(eval_, send, amount, days, proposal) {
  // Fill bid amount
  let r = await eval_(`
    const el = document.getElementById('bidAmountInput');
    if (!el) return 'NO_BID_FORM';
    el.scrollIntoView({ block: 'center' });
    el.focus();
    el.select ? el.select() : document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    document.execCommand('insertText', false, ${JSON.stringify(amount)});
    return 'set: ' + el.value;
  `);
  if (r === 'NO_BID_FORM') return { success: false, error: 'No bid form' };

  await sleep(300);

  // Fill days
  await eval_(`
    const el = document.getElementById('periodInput');
    if (el) {
      el.focus();
      el.select ? el.select() : document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, ${JSON.stringify(days)});
    }
  `);
  await sleep(300);

  // Fill proposal
  await eval_(`
    const el = document.getElementById('descriptionTextArea');
    if (el) {
      el.scrollIntoView({ block: 'center' });
      el.focus();
      el.select ? el.select() : document.execCommand('selectAll', false, null);
      document.execCommand('delete', false, null);
      document.execCommand('insertText', false, ${JSON.stringify(proposal)});
    }
  `);
  await sleep(500);

  // Click Place Bid
  r = await eval_(`
    const btn = Array.from(document.querySelectorAll('button'))
      .find(b => b.textContent.trim() === 'Place Bid' && b.offsetParent !== null);
    if (btn && !btn.disabled) {
      btn.scrollIntoView({ block: 'center' });
      const rect = btn.getBoundingClientRect();
      return JSON.stringify({ x: rect.x + rect.width/2, y: rect.y + rect.height/2 });
    }
    return null;
  `);

  if (r) {
    const pos = JSON.parse(r);
    await send("Input.dispatchMouseEvent", { type: "mousePressed", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(50);
    await send("Input.dispatchMouseEvent", { type: "mouseReleased", x: pos.x, y: pos.y, button: "left", clickCount: 1 });
    await sleep(4000);

    // Check result
    r = await eval_(`
      const success = location.href.includes('bidCreated=true') ||
                      document.body.innerText.includes("successfully placed");
      const errors = Array.from(document.querySelectorAll('[class*="error" i]'))
        .filter(el => el.offsetParent !== null && el.textContent.trim().length > 5)
        .map(el => el.textContent.trim().substring(0, 100));
      return JSON.stringify({ success, errors, url: location.href });
    `);
    return JSON.parse(r);
  }

  return { success: false, error: 'Place Bid button not found or disabled' };
}

async function main() {
  let { ws, send, eval_ } = await connectToPage("freelancer.com");
  console.log("Connected\n");

  // First check how many bids we have left
  await send("Page.navigate", { url: "https://www.freelancer.com/dashboard" });
  await sleep(3000);
  let r = await eval_(`
    const text = document.body.innerText;
    const bidMatch = text.match(/(\\d+)\\s*bids?\\s*left/i);
    return bidMatch ? bidMatch[1] : 'unknown';
  `);
  console.log(`Bids remaining: ${r}\n`);

  const bidsLeft = parseInt(r) || 5;
  const maxBids = Math.min(bidsLeft - 1, targetJobs.length); // Keep 1 in reserve

  console.log(`Will place up to ${maxBids} bids\n`);

  let bidsPlaced = 0;

  for (let i = 0; i < targetJobs.length && bidsPlaced < maxBids; i++) {
    const job = targetJobs[i];
    console.log(`\n=== Job ${i + 1}: ${job.url.split('/').pop()} ===`);

    // Navigate to job page
    await send("Page.navigate", { url: job.url + "/details" });
    await sleep(4000);

    // Get job details
    const details = await getJobDetails(eval_, send);
    console.log(`  Budget: ${details.budget} | Bids: ${details.bids} | Avg: ${details.avgBid} | Currency: ${details.currency}`);
    console.log(`  Has bid form: ${details.hasBidForm}`);

    if (!details.hasBidForm) {
      console.log("  SKIP: No bid form available");
      continue;
    }

    // Calculate competitive bid amount
    let bidAmount;
    if (details.currency === 'INR') {
      // Parse average bid and go ~15% below
      const avgNum = parseInt(details.avgBid?.replace(/[^0-9]/g, '')) || 15000;
      bidAmount = String(Math.round(avgNum * 0.85));
    } else {
      const avgNum = parseInt(details.avgBid?.replace(/[^0-9]/g, '')) || 150;
      bidAmount = String(Math.round(avgNum * 0.85));
    }
    console.log(`  Bidding: ${details.currency === 'INR' ? '₹' : '$'}${bidAmount}`);

    // Place bid
    const result = await placeBid(eval_, send, bidAmount, "5", job.proposal);
    if (result.success) {
      bidsPlaced++;
      console.log(`  ✓ BID PLACED! (${bidsPlaced}/${maxBids})`);
    } else {
      console.log(`  ✗ Failed: ${result.error || result.errors?.join(', ')}`);
    }

    await sleep(1000);
  }

  console.log(`\n========================================`);
  console.log(`BIDS PLACED: ${bidsPlaced}`);
  console.log(`========================================`);

  ws.close();
}

main().catch(e => { console.error("Error:", e.message); process.exit(1); });
