// static/detail_project/js/theme.js
(function () {
  var KEY  = 'ui.theme'; // 'auto' | 'light' | 'dark'
  var DKEY = 'ui.density'; // 'normal' | 'compact'  (opsion
  var root = document.documentElement;
  var btn  = document.getElementById('theme-toggle');
  var icn  = document.getElementById('theme-icon');
  var mql  = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)');

  function savedPref(){
    try { return localStorage.getItem(KEY) || 'auto'; } catch(e){ return 'auto'; }
  }
  function systemTheme(){
    return (mql && mql.matches) ? 'dark' : 'light';
  }
  function resolvedTheme(pref){
    return pref === 'auto' ? systemTheme() : pref;
  }

  function apply(theme){
    root.setAttribute('data-bs-theme', theme);
    root.setAttribute('data-theme', theme); // [P0.1] sinkron untuk selector custom
    var evDetail = { detail: { theme: theme } };
    document.dispatchEvent(new CustomEvent('ui:theme:change', evDetail)); // existing
    document.dispatchEvent(new CustomEvent('theme:changed',  evDetail)); // alias global
    syncMetaColorScheme(theme);
  }

  function syncIcon(pref, theme){
    if (!icn || !btn) return;
    // icon mengikuti resolved theme; tooltip/aria menyebut langkah berikutnya
    icn.className = (theme === 'dark') ? 'bi bi-sun' : 'bi bi-moon-stars';
    btn.setAttribute('aria-pressed', theme === 'dark' ? 'true' : 'false');
    btn.setAttribute('aria-label', theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    // hint kecil untuk mode 'auto' via title
    btn.title = (pref === 'auto') ? 'Auto (click: toggle; Alt+click: force light/dark)' : 'Click to toggle';
  }

  function setPref(pref){
    try { localStorage.setItem(KEY, pref); } catch(e){}
    var theme = resolvedTheme(pref);
    apply(theme);
    syncIcon(pref, theme);
  }

  // ==== Color-scheme meta sinkron (opsional, baik untuk scrollbar native) ====
  function syncMetaColorScheme(theme){
    try{
      var meta = document.querySelector('meta[name="color-scheme"]');
      if (!meta) return;
      // Pilihan 1: kunci ke theme aktif → render native konsisten
      meta.setAttribute('content', theme === 'dark' ? 'dark' : 'light');
      // Jika ingin biarkan UA memilih, ganti baris di atas dengan:
      // meta.setAttribute('content', 'light dark');
    }catch(e){}
  }

  // ==== Density (opsional) — selaras core.css : [data-density="compact"] ====
  function savedDensity(){
    try { return localStorage.getItem(DKEY) || 'normal'; } catch(e){ return 'normal'; }
  }
  function applyDensity(mode){
    if (mode === 'compact') root.setAttribute('data-density', 'compact');
    else root.removeAttribute('data-density');
    document.dispatchEvent(new CustomEvent('ui:density:change', { detail:{ density: mode }}));
  }
  function setDensity(mode){
    try { localStorage.setItem(DKEY, mode); } catch(e){}
    applyDensity(mode);
  }
  function toggleDensity(){
    setDensity(savedDensity() === 'compact' ? 'normal' : 'compact');
  }

  function init(){
    var pref  = savedPref();
    var theme = resolvedTheme(pref);
    apply(theme);
    syncIcon(pref, theme);

    // Klik biasa: light <-> dark (meninggalkan 'auto')
    btn && btn.addEventListener('click', function(e){
      if (e.altKey) return; // [P0.2] biarkan handler Alt menangani
      var next = (resolvedTheme(savedPref()) === 'dark') ? 'light' : 'dark';
      setPref(next);
    });

    // Alt+click untuk kembali ke AUTO cepat
    btn && btn.addEventListener('click', function(e){
      if (!e.altKey) return;
      e.preventDefault();
      e.stopImmediatePropagation(); // [P0.2] cegah eksekusi handler lain
      e.stopPropagation();
      setPref('auto');
    }, true);

    // Jika pref = auto, sinkron dengan perubahan OS
    if (mql){
      var handler = function(){
        if (savedPref() === 'auto') setPref('auto'); // re-resolve & apply
      };
      if (typeof mql.addEventListener === 'function') {
        mql.addEventListener('change', handler);
      } else if (typeof mql.addListener === 'function') {
        // Safari lama
        try { mql.addListener(handler); } catch(e){}
      }
    }

    // [P0.O1] Fallback delegasi untuk elemen yang punya data-action="toggle-theme"
    document.addEventListener('click', function(e){
      var t = e.target.closest('[data-action="toggle-theme"]');
      if (!t) return;
      // Jika tombol utama ada dan itu yang diklik, biarkan handler utama bekerja
      if (btn && (t === btn || t.contains(btn) || btn.contains(t))) return;

      if (e.altKey) {
        e.preventDefault();
        setPref('auto');
      } else {
        var next = (resolvedTheme(savedPref()) === 'dark') ? 'light' : 'dark';
        setPref(next);
      }
    });
    
    // ==== Delegasi toggle density (opsional) ====
    document.addEventListener('click', function(e){
      var t = e.target.closest('[data-action="toggle-density"]');
      if (!t) return;
      e.preventDefault();
      toggleDensity();
    });

    // Apply density awal dari storage (no-op kalau normal)
    applyDensity(savedDensity());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
