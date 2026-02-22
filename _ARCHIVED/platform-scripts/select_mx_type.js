(function() {
  var combo = document.querySelectorAll("[role=combobox]");
  var typeCombo = null;
  combo.forEach(function(c) { if (c.textContent.trim() === "Type") typeCombo = c; });
  if (typeCombo) {
    typeCombo.click();
    return "clicked Type combobox";
  }
  return "Type combobox not found";
})();