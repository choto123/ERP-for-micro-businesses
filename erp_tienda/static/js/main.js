function openModal(id) {
  document.getElementById(id).classList.add('open');
}

function closeModal(id) {
  document.getElementById(id).classList.remove('open');
  const modal = document.getElementById(id);
  modal.querySelectorAll('input[type=text],input[type=email],input[type=number],textarea').forEach(el => {
    if (!el.id.includes('fecha')) el.value = '';
  });
  modal.querySelectorAll('input[type=hidden]').forEach(el => el.value = '');
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
  overlay.addEventListener('click', e => {
    if (e.target === overlay) overlay.classList.remove('open');
  });
});

function showToast(msg, type = 'ok') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = 'toast show' + (type === 'error' ? ' error' : '');
  setTimeout(() => t.classList.remove('show'), 2800);
}

// Deshabilitar botones de acción si el servidor indica solo lectura
document.addEventListener('DOMContentLoaded', () => {
  const banner = document.querySelector('.readonly-banner');
  if (banner) {
    document.querySelectorAll('.btn-primary, .btn-danger').forEach(btn => {
      btn.disabled = true;
      btn.title = 'No tienes permisos para esta acción';
    });
  }
});
