// Check status of all signup tabs
const CDP_HTTP = "http://localhost:9222";

async function main() {
  const tabsRes = await fetch(`${CDP_HTTP}/json`);
  const tabs = await tabsRes.json();

  console.log("=== All open tabs ===\n");
  for (const tab of tabs) {
    if (tab.url && !tab.url.startsWith('chrome') && !tab.url.startsWith('devtools')) {
      console.log(`  ${tab.title?.substring(0, 60)} - ${tab.url.substring(0, 80)}`);
    }
  }

  // Find Freelancer signup tab
  const fl = tabs.find(t => t.url.includes("freelancer.com/signup"));
  if (fl) {
    console.log("\n=== Freelancer.com Signup Tab ===");
    console.log("URL:", fl.url);
    console.log("Title:", fl.title);
  } else {
    console.log("\nNo Freelancer signup tab found");
    const flAny = tabs.find(t => t.url.includes("freelancer.com"));
    if (flAny) console.log("  But found:", flAny.url);
  }
}

main().catch(console.error);
