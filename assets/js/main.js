/* main.js — comportamento progressivo (site funciona sem JS) */

/* Copy-to-clipboard para o botão de e-mail na seção Contato */
document.addEventListener('DOMContentLoaded', () => {
  const copyBtns = document.querySelectorAll('[data-copy]');

  copyBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      const text = btn.dataset.copy;
      const copiedLabel = btn.dataset.copiedLabel || 'Copiado!';
      const originalLabel = btn.textContent;

      navigator.clipboard.writeText(text).then(() => {
        btn.textContent = copiedLabel;
        btn.setAttribute('aria-pressed', 'true');
        setTimeout(() => {
          btn.textContent = originalLabel;
          btn.removeAttribute('aria-pressed');
        }, 2000);
      });
    });
  });
});
