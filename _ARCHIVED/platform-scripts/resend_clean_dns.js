(function() {
  var tables = document.querySelectorAll("table");
  var records = [];
  tables.forEach(function(t) {
    var rows = t.querySelectorAll("tr");
    rows.forEach(function(r, ri) {
      if (ri === 0) return;
      var cells = r.querySelectorAll("td");
      if (cells.length >= 3) {
        var copyBtns = r.querySelectorAll("button");
        var values = [];
        cells.forEach(function(c) {
          var code = c.querySelector("code, span[class*=mono], [class*=code]");
          values.push(code ? code.textContent.trim() : c.textContent.trim());
        });
        records.push(values.join(" | "));
      }
    });
  });
  return records.join("\n");
})();
