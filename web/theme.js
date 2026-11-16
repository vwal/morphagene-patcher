// Apply the saved theme before the stylesheet paints. Until a theme is chosen,
// follow the device preference. Storage may be unavailable in private contexts.
(() => {
  const key = 'morphagene-patcher-theme';
  const root = document.documentElement;
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  const validTheme = value => value === 'light' || value === 'dark';
  let preference = null;
  try {
    const saved = window.localStorage.getItem(key);
    if (validTheme(saved)) preference = saved;
  } catch (_) { /* The switch still works without persistence. */ }

  function apply() {
    const theme = preference || (system.matches ? 'dark' : 'light');
    root.dataset.theme = theme;
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
      toggle.setAttribute('aria-checked', String(theme === 'dark'));
      toggle.title = theme === 'dark' ? 'Switch to day mode' : 'Switch to night mode';
      document.getElementById('theme-label').textContent = theme === 'dark' ? 'Night' : 'Day';
    }
  }

  apply();
  system.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = validTheme(event.newValue) ? event.newValue : null;
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('theme-toggle');
    toggle.addEventListener('click', () => {
      preference = root.dataset.theme === 'dark' ? 'light' : 'dark';
      try { window.localStorage.setItem(key, preference); } catch (_) {}
      apply();
    });
    apply();
    toggle.hidden = false;
  }, {once: true});
})();
