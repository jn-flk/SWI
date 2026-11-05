// Highlights selected seats and shows their count; the form works without JS too.
(function () {
  const form = document.getElementById("seat-form");
  const counter = document.getElementById("selected-count");
  if (!form || !counter) return;

  function update() {
    const boxes = form.querySelectorAll('input[name="seats"]');
    let count = 0;
    boxes.forEach(function (box) {
      box.parentElement.classList.toggle("seat--selected", box.checked);
      if (box.checked) count += 1;
    });
    counter.textContent = count;
  }

  form.addEventListener("change", update);
  update();
})();
