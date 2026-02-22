(function() {
  var btn = Array.from(document.querySelectorAll("button")).find(function(b) { return b.textContent.trim() === "Create Account"; });
  var email = document.getElementById("email");
  var pass = document.getElementById("password");
  var result = {
    btnFound: !!btn,
    btnDisabled: btn ? btn.disabled : null,
    btnType: btn ? btn.type : null,
    emailValue: email ? email.value : null,
    passLen: pass ? pass.value.length : null,
    bodySnippet: document.body.innerHTML.substring(0, 1000)
  };
  return JSON.stringify(result);
})();
