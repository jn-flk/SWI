// Counts down the seat hold; uses the server time so a wrong client clock does not matter.
(function () {
  const element = document.querySelector("[data-hold-until]");
  if (!element) return;
  const remainingAtLoad = Number(element.dataset.holdUntil) - Number(element.dataset.now);
  const loadedAt = Date.now();

  function tick() {
    const left = Math.max(0, Math.round(remainingAtLoad - (Date.now() - loadedAt) / 1000));
    if (left === 0) {
      element.classList.add("hold--expired");
      element.innerHTML = 'Držení sedadel vypršelo. <a href="' + element.dataset.expiredUrl
        + '">Vyberte sedadla znovu</a>.';
      document.querySelectorAll("main button[type=submit]").forEach(function (button) {
        button.disabled = true;
      });
      return;
    }
    const seconds = String(left % 60).padStart(2, "0");
    element.innerHTML = 'Sedadla jsou držena ještě <strong class="hold__time">'
      + Math.floor(left / 60) + ":" + seconds + "</strong>.";
    setTimeout(tick, 1000);
  }
  tick();
})();
