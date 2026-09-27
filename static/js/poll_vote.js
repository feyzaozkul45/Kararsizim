// Poll detail page: animate result bars and vote with fetch (no page reload).
// Without JavaScript the form still works as a normal POST + redirect.
(function () {
  var TINT_COUNT = 5;

  var form = document.getElementById("vote-form");
  var resultsBox = document.getElementById("results");
  var totalBox = document.getElementById("total-votes");
  var hiddenNote = document.getElementById("hidden-note");
  var errorBox = document.getElementById("vote-error");

  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function formatPercent(value) {
    return String(Math.round(value * 10) / 10).replace(".", ",");
  }

  // Grow each bar from 0 to its percentage.
  function animateBars(root) {
    var bars = root.querySelectorAll(".result-bar");
    bars.forEach(function (bar) {
      var target = bar.getAttribute("data-percent") + "%";
      if (reduceMotion) {
        bar.style.width = target;
        return;
      }
      bar.style.width = "0";
      requestAnimationFrame(function () {
        requestAnimationFrame(function () {
          bar.style.width = target;
        });
      });
    });
  }

  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function renderResults(data) {
    resultsBox.textContent = "";
    data.results.forEach(function (result, index) {
      var mine = result.id === data.voted_option_id;
      var row = el("div", "result tint-" + (index % TINT_COUNT) + (mine ? " result-mine" : ""));

      var bar = el("div", "result-bar");
      bar.setAttribute("data-percent", result.percent);

      var line = el("div", "result-row");
      line.appendChild(el("span", "result-text", (mine ? "✓ " : "") + result.text));
      line.appendChild(el("span", "result-figures", result.votes + " oy · %" + formatPercent(result.percent)));

      row.appendChild(bar);
      row.appendChild(line);
      resultsBox.appendChild(row);
    });

    resultsBox.hidden = false;
    animateBars(resultsBox);

    // The vote form (and its focused button) is gone now; move focus to the
    // results so keyboard/screen-reader users land somewhere meaningful
    // instead of being dropped back at the top of the page.
    resultsBox.setAttribute("tabindex", "-1");
    resultsBox.focus();

    totalBox.textContent = "";
    totalBox.appendChild(document.createTextNode("Toplam "));
    totalBox.appendChild(el("strong", "", data.total_votes));
    totalBox.appendChild(document.createTextNode(" oy"));
    if (hiddenNote) hiddenNote.remove();
  }

  function showError(message) {
    if (!errorBox) return;
    errorBox.textContent = message;
    errorBox.hidden = false;
  }

  if (resultsBox && !resultsBox.hidden) animateBars(resultsBox);
  if (!form || !resultsBox) return;

  form.addEventListener("submit", function (event) {
    var submitter = event.submitter;
    if (!submitter || !submitter.value) return; // no option chosen, nothing to lock

    // Lock the buttons immediately so a double click can't fire two votes.
    // This also covers the no-fetch fallback below: the buttons stay disabled
    // until the page navigates away with the normal POST.
    var buttons = form.querySelectorAll("button");
    buttons.forEach(function (button) { button.disabled = true; });
    if (errorBox) errorBox.hidden = true;

    if (!window.fetch) return; // fall back to a normal POST

    event.preventDefault();
    var body = new FormData(form);
    body.set("option", submitter.value);
    var csrf = form.querySelector("input[name='csrfmiddlewaretoken']");

    fetch(form.action, {
      method: "POST",
      body: body,
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json",
        "X-CSRFToken": csrf ? csrf.value : ""
      }
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { status: response.status, data: data };
        });
      })
      .then(function (result) {
        if (result.data.ok) {
          form.remove();
          if (errorBox) errorBox.remove();
          renderResults(result.data);
          return;
        }
        showError(result.data.error || "Bir hata oluştu.");
        if (result.status === 409 || result.status === 403) {
          setTimeout(function () { window.location.reload(); }, 1500);
        } else {
          buttons.forEach(function (button) { button.disabled = false; });
        }
      })
      .catch(function () {
        showError("Bağlantı hatası. Lütfen tekrar dene.");
        buttons.forEach(function (button) { button.disabled = false; });
      });
  });
})();
