import { writeFileSync } from 'fs';
const CDP_HTTP = "http://localhost:9222";

(async () => {
  try {
    const tabs = await (await fetch(`${CDP_HTTP}/json`)).json();
    const result = tabs.map(t => ({
      title: t.title.substring(0, 60),
      url: t.url.substring(0, 80),
      type: t.type,
      id: t.id
    }));
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', JSON.stringify(result, null, 2));
  } catch(e) {
    writeFileSync('D:\\_CLAUDE-TOOLS\\cw_output.txt', 'Error: ' + e.message);
  }
  process.exit(0);
})();
