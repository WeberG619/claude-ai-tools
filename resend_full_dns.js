(function() {
  var cells = document.querySelectorAll("td");
  var results = [];
  cells.forEach(function(c) {
    var text = c.innerText.trim();
    if (text.length > 10) {
      results.push(text);
    }
  });
  return results.join("\n---\n");
})();
