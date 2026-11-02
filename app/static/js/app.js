"""Small progressive enhancements shared across pages."""

document.addEventListener("DOMContentLoaded", () => {
  // Keep flash notifications readable, then gently dismiss them.
  const flashes = document.querySelectorAll(".flash");
  flashes.forEach((flash) => {
    window.setTimeout(() => {
      flash.style.transition = "opacity .35s ease";
      flash.style.opacity = "0";
      window.setTimeout(() => flash.remove(), 400);
    }, 6500);
  });

  // Prevent accidental double submissions on normal POST forms.
  document.querySelectorAll("form").forEach((form) => {
    form.addEventListener("submit", () => {
      const submitButton = form.querySelector('button[type="submit"]');
      if (submitButton && !form.hasAttribute("onsubmit")) {
        submitButton.dataset.originalText = submitButton.textContent;
        submitButton.disabled = true;
        submitButton.textContent = "Please wait…";
      }
    });
  });
});
