import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";
const out = [];
const L = (msg) => out.push(msg);

(async () => {
  // Check /json/list for ALL targets
  const targets = await (await fetch(`${CDP_HTTP}/json/list`)).json();
  L("=== ALL TARGETS ===");
  targets.forEach(t => L(t.type + " | " + t.title?.substring(0,60) + " | " + t.url?.substring(0,150)));

  // Also try /json/new to see if there are hidden windows
  L("\n=== TARGET COUNT: " + targets.length + " ===");

  // Check for any page targets
  const pages = targets.filter(t => t.type === 'page');
  L("Page targets: " + pages.length);
  pages.forEach(p => L("  " + p.url));

  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(0);
})().catch(e => {
  L("Error: " + e.message);
  writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', out.join('\n'));
  process.exit(1);
});
