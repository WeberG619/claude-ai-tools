// List all Chrome tabs
const CDP_HTTP = "http://localhost:9222";

async function main() {
  const res = await fetch(`${CDP_HTTP}/json`);
  const tabs = await res.json();
  console.log(`Found ${tabs.length} tabs:\n`);
  tabs.forEach((t, i) => {
    console.log(`${i+1}. [${t.type}] ${t.title}`);
    console.log(`   URL: ${t.url.substring(0, 120)}`);
    console.log();
  });
}

main().catch(e => console.error("Error:", e.message));
