// Adds an eye button to every password field; Tab skips it and moves to the next field.
(function () {
  const svg = '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" fill="none" '
    + 'stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">';
  const eye = svg + '<path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12z"/>'
    + '<circle cx="12" cy="12" r="3"/></svg>';
  const eyeOff = svg + '<path d="M17.94 17.94A10.07 10.07 0 0 1 12 19c-7 0-11-7-11-7'
    + 'a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 7 11 7'
    + 'a18.5 18.5 0 0 1-2.16 3.19M14.12 14.12a3 3 0 1 1-4.24-4.24"/>'
    + '<line x1="1" y1="1" x2="23" y2="23"/></svg>';

  document.querySelectorAll('input[type="password"]').forEach(function (input) {
    const wrapper = document.createElement("div");
    wrapper.className = "password-field";
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const button = document.createElement("button");
    button.type = "button";
    button.className = "password-toggle";
    button.tabIndex = -1;

    function render(shown) {
      button.innerHTML = shown ? eyeOff : eye;
      button.setAttribute("aria-label", shown ? "Skrýt heslo" : "Zobrazit heslo");
      button.title = button.getAttribute("aria-label");
    }

    button.addEventListener("mousedown", function (event) {
      event.preventDefault();  // keep focus in the input
    });
    button.addEventListener("click", function () {
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      render(show);
      input.focus();
    });
    render(false);
    wrapper.appendChild(button);
  });
})();
