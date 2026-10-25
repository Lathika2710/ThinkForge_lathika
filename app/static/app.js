// 1) CSRF token on every POST form
const tok = document.querySelector('meta[name=csrf]').content;
document.querySelectorAll('form[method=post]').forEach(f => {
  if (!f.querySelector('[name=csrf_token]')) {
    const i = document.createElement('input'); i.type = 'hidden'; i.name = 'csrf_token'; i.value = tok; f.appendChild(i);
  }
});

// 2) Auto refresh (worker dashboard / SOS status) unless the user is typing
const ms = parseInt(document.body.dataset.refresh || '0');
if (ms) setInterval(() => {
  const a = document.activeElement;
  if (!a || !['INPUT', 'TEXTAREA', 'SELECT'].includes(a.tagName)) location.reload();
}, ms);
