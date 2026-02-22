(function() {
  var inputs = document.querySelectorAll("input");
  var result = [];
  inputs.forEach(function(inp, i) {
    result.push("INPUT" + i + ": type=" + inp.type + " id=" + inp.id + " name=" + inp.name + " placeholder=" + inp.placeholder);
  });
  return result.join("\n");
})();