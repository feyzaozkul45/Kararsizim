// Site-wide helpers: auto-hide Django messages and confirm destructive forms.
(function () {
  document.querySelectorAll("[data-autohide]").forEach(function (el) {
    setTimeout(function () {
      el.classList.add("message-hide");
      setTimeout(function () { el.remove(); }, 500);
    }, 5000);
  });

  document.addEventListener("submit", function (event) {
    var message = event.target.getAttribute("data-confirm");
    if (message && !window.confirm(message)) {
      event.preventDefault();
    }
  });
})();
