(function() {
  var combo = document.querySelector("[role=combobox]");
  if (combo) {
    combo.click();
    return "clicked Type combobox: " + combo.textContent.trim();
  }
  return "combobox not found";
})();