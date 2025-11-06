// dashboard/static/dashboard/js/dashboard.js
document.addEventListener('DOMContentLoaded', function () {
  // === Toggle List/Grid (opsional) ===
  const listViewBtn = document.getElementById('list-view-btn');
  const gridViewBtn = document.getElementById('grid-view-btn');
  const listView = document.getElementById('list-view');
  const gridView = document.getElementById('grid-view');

  if (gridViewBtn && listViewBtn && gridView && listView) {
    gridViewBtn.addEventListener('click', () => {
      listView.classList.add('d-none');
      gridView.classList.remove('d-none');
      listViewBtn.classList.remove('active');
      gridViewBtn.classList.add('active');
    });

    listViewBtn.addEventListener('click', () => {
      gridView.classList.add('d-none');
      listView.classList.remove('d-none');
      gridViewBtn.classList.remove('active');
      listViewBtn.classList.add('active');
    });
  }

  // === Shortcut Keyboard ===
  const searchInput = document.getElementById('search-input');
  document.addEventListener('keydown', function (e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      if (searchInput) searchInput.focus();
    }
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n') {
      e.preventDefault();
      const firstInput = document.querySelector('input[name$="-nama"]');
      if (firstInput) firstInput.focus();
    }
  });

  // === Scroll ke tabel setelah submit (opsional) ===
  const urlParams = new URLSearchParams(window.location.search);
  if (urlParams.get("submitted") === "true") {
    const tableSection = document.querySelector('.dashboard-table-wrapper');
    if (tableSection) tableSection.scrollIntoView({ behavior: 'smooth' });
    if (window.history.replaceState) {
      const cleanUrl = window.location.origin + window.location.pathname;
      window.history.replaceState({}, document.title, cleanUrl);
    }
  }

  // === Anti Double Submit: Dashboard Form ===
  const dashForm = document.querySelector('form.dashboard-form');
  if (dashForm) {
    dashForm.addEventListener('submit', function (e) {
      const btn = dashForm.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        btn.dataset.originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Menyimpan...';
      }
    });
  }

  // === Anti Double Submit: Upload Form ===
  const uploadForm = document.getElementById('upload-form');
  if (uploadForm) {
    const uploadBtn = document.getElementById('upload-submit');
    uploadForm.addEventListener('submit', function () {
      if (uploadBtn) {
        uploadBtn.disabled = true;
        uploadBtn.dataset.originalText = uploadBtn.innerHTML;
        uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>Mengunggah...';
      }
    });
  }
});

// Safety: bersihkan modal-backdrop jika tertinggal setelah modal ditutup
document.addEventListener('hidden.bs.modal', function () {
  document.querySelectorAll('.modal-backdrop').forEach(el => el.remove());
  document.body.classList.remove('modal-open');
});

// ============================================================================
// FORM MODE TOGGLE (Simple vs Full Mode)
// ============================================================================
document.addEventListener('DOMContentLoaded', function() {
  const formTable = document.getElementById('formset-table');
  const btnSimple = document.getElementById('formModeSimple');
  const btnFull = document.getElementById('formModeFull');

  if (!formTable || !btnSimple || !btnFull) return;

  // Set default mode to Simple
  formTable.classList.add('mode-simple');

  // Simple Mode Button
  btnSimple.addEventListener('click', function() {
    formTable.classList.remove('mode-full');
    formTable.classList.add('mode-simple');
    btnSimple.classList.add('active');
    btnFull.classList.remove('active');

    // Save preference to localStorage
    try {
      localStorage.setItem('formMode', 'simple');
    } catch(e) {}
  });

  // Full Mode Button
  btnFull.addEventListener('click', function() {
    formTable.classList.remove('mode-simple');
    formTable.classList.add('mode-full');
    btnFull.classList.add('active');
    btnSimple.classList.remove('active');

    // Save preference to localStorage
    try {
      localStorage.setItem('formMode', 'full');
    } catch(e) {}
  });

  // Load saved preference from localStorage
  try {
    const savedMode = localStorage.getItem('formMode');
    if (savedMode === 'full') {
      btnFull.click();
    }
  } catch(e) {}
});