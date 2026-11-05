(function () {
  const element = document.querySelector("[data-hold-until]");
  if (!element) return;
  const time = element.querySelector(".hold__time");
  const remainingAtLoad = Number(element.dataset.holdUntil) - Number(element.dataset.now);
  const loadedAt = Date.now();

  function tick() {
    const left = Math.max(0, Math.round(remainingAtLoad - (Date.now() - loadedAt) / 1000));
    if (left === 0) {
      window.location.replace(element.dataset.expiredUrl);
      return;
    }
    time.textContent = Math.ceil(left / 60);
    setTimeout(tick, 1000);
  }
  tick();
})();
