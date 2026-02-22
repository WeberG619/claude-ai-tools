const CDP_HTTP = "http://localhost:9222";

(async () => {
  const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
  console.log("All page targets:");
  tabs.filter(t => t.type === "page").forEach(t => console.log("  " + t.url?.substring(0, 120)));
})().catch(e => console.error("Error:", e.message));
