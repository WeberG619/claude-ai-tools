(function() {
  var tables = document.querySelectorAll("table");
  var records = [];
  tables.forEach(function(t, ti) {
    var rows = t.querySelectorAll("tr");
    rows.forEach(function(r, ri) {
      if (ri === 0) return;
      var cells = r.querySelectorAll("td");
      if (cells.length >= 3) {
        records.push({
          table: ti,
          type: cells[0] ? cells[0].textContent.trim() : "",
          name: cells[1] ? cells[1].textContent.trim() : "",
          content: cells[2] ? cells[2].textContent.trim() : "",
          ttl: cells[3] ? cells[3].textContent.trim() : "",
          priority: cells[4] ? cells[4].textContent.trim() : ""
        });
      }
    });
  });
  return JSON.stringify(records, null, 2);
})();
