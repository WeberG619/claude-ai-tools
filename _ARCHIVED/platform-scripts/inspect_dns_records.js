(function() {
  var result = [];
  var rows = document.querySelectorAll("tr, [class*='record'], [class*='Record'], [class*='row'], [class*='Row']");
  rows.forEach(function(r, i) {
    if (i < 30) {
      var text = r.textContent.trim().replace(/\s+/g, " ").substring(0, 150);
      if (text.length > 5) result.push("ROW" + i + ": " + text);
    }
  });
  var tables = document.querySelectorAll("table");
  tables.forEach(function(t, i) {
    result.push("TABLE" + i + ": " + t.textContent.trim().replace(/\s+/g, " ").substring(0, 300));
  });
  var custom = document.querySelector("[class*='custom'], [class*='Custom']");
  if (custom) {
    result.push("CUSTOM SECTION: " + custom.textContent.trim().replace(/\s+/g, " ").substring(0, 500));
  }
  var body = document.body.innerText;
  var idx = body.indexOf("Custom records");
  if (idx > -1) {
    result.push("AFTER CUSTOM: " + body.substring(idx, idx + 800).replace(/\s+/g, " "));
  }
  return result.join("\n");
})();