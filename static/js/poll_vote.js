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
    if (!submitter || !submitter.value || !window.fetch) return; // fall back to a normal POST

    event.preventDefault();
    var buttons = form.querySelectorAll("button");
    buttons.forEach(function (button) { button.disabled = true; });
    if (errorBox) errorBox.hidden = true;

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
