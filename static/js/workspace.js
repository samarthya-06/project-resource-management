// Native server forms remain usable without JavaScript.
const summary = document.querySelector('[data-error-summary]');
if (summary) summary.focus();
document.querySelectorAll('form[data-saving]').forEach((form) => {
  form.addEventListener('submit', () => {
    form.setAttribute('aria-busy', 'true');
    const status = form.querySelector('.saving-status');
    if (status) status.hidden = false;
    form.querySelectorAll('button[type="submit"]').forEach((button) => { button.disabled = true; });
  });
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[data-saving]').forEach((form) => {
    form.removeAttribute('aria-busy');
    form.querySelectorAll('button[type="submit"]').forEach((button) => { button.disabled = false; });
    const status = form.querySelector('.saving-status');
    if (status) status.hidden = true;
  });
});
