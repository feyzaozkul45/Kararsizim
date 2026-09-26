// Poll creation form: add/remove option inputs (2–5) and a live character counter.
(function () {
  var MIN_OPTIONS = 2;
  var MAX_OPTIONS = 5;

  var container = document.getElementById("option-inputs");
  var addButton = document.getElementById("add-option");
  var question = document.querySelector("#poll-form input[name='question']");
  var counter = document.getElementById("question-count");
  if (!container || !addButton) return;

  function rows() {
    return container.querySelectorAll(".option-input-row");
  }

  // Keep placeholders, labels and remove buttons consistent after every change.
  function refresh() {
    var list = rows();
    list.forEach(function (row, index) {
      var input = row.querySelector("input");
      input.placeholder = "Seçenek " + (index + 1);
      input.setAttribute("aria-label", "Seçenek " + (index + 1));

      var remove = row.querySelector(".remove-option");
      if (index >= MIN_OPTIONS && !remove) {
        row.appendChild(createRemoveButton());
      } else if (index < MIN_OPTIONS && remove) {
        remove.remove();
      }
    });
    addButton.disabled = list.length >= MAX_OPTIONS;
  }

  function createRemoveButton() {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "remove-option";
    button.setAttribute("aria-label", "Seçeneği sil");
    button.textContent = "×";
    return button;
  }

  addButton.addEventListener("click", function () {
    if (rows().length >= MAX_OPTIONS) return;

    var row = document.createElement("div");
    row.className = "option-input-row";

    var input = document.createElement("input");
    input.type = "text";
    input.name = "option";
    input.className = "form-control";
    input.maxLength = 80;

    row.appendChild(input);
    container.appendChild(row);
    refresh();
    input.focus();
  });

  container.addEventListener("click", function (event) {
    var button = event.target.closest(".remove-option");
    if (!button || rows().length <= MIN_OPTIONS) return;
    button.closest(".option-input-row").remove();
    refresh();
    addButton.focus();
  });

  if (question && counter) {
    var update = function () {
      counter.textContent = question.value.length;
    };
    question.addEventListener("input", update);
    update();
  }

  refresh();
})();
