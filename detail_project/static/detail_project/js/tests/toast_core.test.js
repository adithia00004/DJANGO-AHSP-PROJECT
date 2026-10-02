/**
 * T-2/T-3/T-6 (docs/RENCANA_PERAPIAN_PROYEK_20261001.md §5) — perilaku toast.
 *
 * Keluhan owner 2026-10-01: satu aksi memunculkan dua toast, dan toast tidak
 * hilang sendiri. Tes menjalankan js/core/toast.js & messages_modal.js asli
 * (happy-dom + timer palsu), bukan sekadar grep sumber.
 */
import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const JS_DIR = resolve(__dirname, '..');
const TOAST_SRC = readFileSync(resolve(JS_DIR, 'core', 'toast.js'), 'utf-8');
const MESSAGES_SRC = readFileSync(resolve(JS_DIR, 'messages_modal.js'), 'utf-8');

function loadToast() {
  delete window.DP;
  delete window.showToast;
  document.body.innerHTML = '';
  // eslint-disable-next-line no-new-func
  new Function(TOAST_SRC)();
  return window.DP.toast;
}

const visible = () => Array.from(document.querySelectorAll('.dp-toast:not(.dp-toast-hide)'));

describe('core/toast.js', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  test('objek {duration, position} sebagai argumen kedua tetap hilang sendiri (T-F1)', () => {
    const toast = loadToast();
    toast.success('Laporan berhasil diunduh.', { duration: 3000, position: 'top-right' });
    expect(visible()).toHaveLength(1);
    vi.advanceTimersByTime(3000);
    expect(visible()).toHaveLength(0);
  });

  test.each([
    ['success', undefined, 3000],
    ['info', 0, 3000],
    ['warning', -5, 5000],
    ['error', 'abc', 6000],
    ['success', NaN, 3000],
    ['info', 1500, 1500],
  ])('durasi %s dengan nilai %s -> %i ms (tidak ada toast biasa yang menetap)', (type, raw, expected) => {
    const toast = loadToast();
    toast.show('pesan', type, raw);
    vi.advanceTimersByTime(expected - 1);
    expect(visible()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(visible()).toHaveLength(0);
  });

  test('durasi dibatasi maksimum 60 detik', () => {
    const toast = loadToast();
    toast.info('lama', 10 * 60 * 1000);
    vi.advanceTimersByTime(60000);
    expect(visible()).toHaveLength(0);
  });

  test('danger/warn dikenali lewat show() maupun DP.toast[type] (T-F5)', () => {
    const toast = loadToast();
    toast.show('gagal', 'danger');
    toast.danger('gagal lagi');
    toast.warn('awas');
    const toasts = visible();
    expect(toasts[0].className).toContain('dp-toast-error');
    expect(toasts[0].querySelector('i').className).toContain('bi-x-circle-fill');
    expect(toasts[1].className).toContain('dp-toast-error');
    expect(toasts[2].className).toContain('dp-toast-warning');
  });

  test('pesan sama yang masih tampil tidak digandakan; diberi penanda xN dan timer diulang (T-F6)', () => {
    const toast = loadToast();
    const first = toast.success('Data tersimpan');
    vi.advanceTimersByTime(2000);
    const second = toast.success('Data tersimpan');
    expect(second).toBe(first);
    expect(visible()).toHaveLength(1);
    expect(first.querySelector('.dp-toast-count').textContent).toBe(' ×2');
    vi.advanceTimersByTime(2999); // timer lama (sisa 1 dtk) sudah dibatalkan
    expect(visible()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(visible()).toHaveLength(0);
  });

  test('penanda xN memakai textContent, bukan HTML dari pesan', () => {
    const toast = loadToast();
    toast.info('<img src=x onerror=alert(1)>');
    const el = toast.info('<img src=x onerror=alert(1)>');
    expect(el.querySelector('img')).toBeNull();
    expect(el.textContent).toContain('<img src=x');
  });

  test('pesan sama sesudah toast lama hilang membuat toast baru', () => {
    const toast = loadToast();
    toast.success('Data tersimpan');
    vi.advanceTimersByTime(3300);
    toast.success('Data tersimpan');
    expect(visible()).toHaveLength(1);
    expect(visible()[0].querySelector('.dp-toast-count').hidden).toBe(true);
  });

  test('maksimal 3 toast tampil termasuk yang baru (T-F10)', () => {
    const toast = loadToast();
    ['a', 'b', 'c', 'd'].forEach((m) => toast.info(m));
    const shown = visible();
    expect(shown).toHaveLength(3);
    expect(shown.map((t) => t.textContent.trim())).toEqual(['b', 'c', 'd']);
  });

  test('batas jumlah menggusur toast biasa sebelum loading', () => {
    const toast = loadToast();
    const spinner = toast.loading('Memproses...');
    ['a', 'b', 'c'].forEach((m) => toast.info(m));
    expect(visible()).toHaveLength(3);
    expect(visible()).toContain(spinner);
  });

  test('loading: dua operasi dengan pesan sama punya handle sendiri', () => {
    const toast = loadToast();
    const one = toast.loading('Memeriksa...');
    const two = toast.loading('Memeriksa...');
    expect(one).not.toBe(two);
    toast.dismiss(one);
    expect(visible()).toEqual([two]);
  });

  test('loading menetap sampai ditutup, dengan batas aman 60 detik', () => {
    const toast = loadToast();
    toast.loading('Memproses...');
    vi.advanceTimersByTime(59999);
    expect(visible()).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(visible()).toHaveLength(0);
  });

  test('bentuk objek show({...}) tetap didukung', () => {
    const toast = loadToast();
    const el = toast.show({ message: 'Impor selesai', type: 'success', title: 'Referensi', duration: 1000 });
    expect(el.querySelector('.dp-toast-title').textContent).toBe('Referensi');
    vi.advanceTimersByTime(1000);
    expect(visible()).toHaveLength(0);
  });

  test('tombol aksi dirender sebagai teks, memanggil callback, lalu menutup toast', () => {
    const toast = loadToast();
    const onClick = vi.fn();
    const el = toast.show({
      message: 'Impor selesai',
      type: 'success',
      duration: 0,
      actions: [{ label: '<Undo>', onClick }],
    });
    const button = el.querySelector('.dp-toast-action');

    expect(button.textContent).toBe('<Undo>');
    expect(el.querySelector('undo')).toBeNull();
    button.click();
    expect(onClick).toHaveBeenCalledOnce();
    expect(el.classList.contains('dp-toast-hide')).toBe(true);
    expect(visible()).toHaveLength(0);
  });

  test('toast aksi dengan pesan sama tetap punya callback masing-masing', () => {
    const toast = loadToast();
    const firstAction = vi.fn();
    const secondAction = vi.fn();
    const first = toast.show({ message: 'Undo tersedia', actions: [{ label: 'Undo', onClick: firstAction }] });
    const second = toast.show({ message: 'Undo tersedia', actions: [{ label: 'Undo', onClick: secondAction }] });

    expect(first).not.toBe(second);
    first.querySelector('.dp-toast-action').click();
    expect(firstAction).toHaveBeenCalledOnce();
    expect(secondAction).not.toHaveBeenCalled();
    expect(visible()).toEqual([second]);
  });

  test('window.showToast & DP.core.toast memakai aturan yang sama', () => {
    loadToast();
    window.showToast('x', 'danger');
    window.DP.core.toast.show('y', 'success', { duration: 2000, position: 'top-right' });
    expect(visible().map((t) => t.className)).toEqual([
      expect.stringContaining('dp-toast-error'),
      expect.stringContaining('dp-toast-success'),
    ]);
    vi.advanceTimersByTime(6000);
    expect(visible()).toHaveLength(0);
  });
});

describe('messages_modal.js (K-6/T-6)', () => {
  function renderMessages(items) {
    loadToast();
    document.body.insertAdjacentHTML('beforeend', `
      <div id="messagesModal"><div id="messagesModalHeader"></div>
        <h5 id="messagesModalTitle"></h5><div id="messagesModalBody"></div></div>
      <div id="django-messages-data">${items
        .map(([tags, message]) => `<div class="message-item" data-tags="${tags}" data-message="${message}"></div>`)
        .join('')}</div>`);
    const shown = [];
    window.bootstrap = {
      Modal: class {
        constructor(el) { this.el = el; }
        show() { shown.push(document.getElementById('messagesModalBody').textContent); }
      },
    };
    // eslint-disable-next-line no-new-func
    new Function(MESSAGES_SRC)();
    return shown;
  }

  beforeEach(() => vi.useFakeTimers());
  afterEach(() => {
    vi.useRealTimers();
    delete window.bootstrap;
  });

  test('sukses/info jadi toast yang hilang sendiri; tanpa modal', () => {
    const modal = renderMessages([['success', 'Proyek berhasil disimpan']]);
    expect(modal).toEqual([]);
    expect(visible()).toHaveLength(1);
    expect(visible()[0].textContent).toContain('Proyek berhasil disimpan');
    vi.advanceTimersByTime(3000);
    expect(visible()).toHaveLength(0);
  });

  test('error/peringatan tetap modal; pesan campuran tampil masing-masing sekali', () => {
    const modal = renderMessages([
      ['success', 'Tersimpan'],
      ['warning', 'Cek tanggal'],
      ['error', 'Gagal impor'],
    ]);
    expect(visible()).toHaveLength(1);
    expect(modal).toHaveLength(1);
    expect(modal[0]).toContain('Cek tanggal');
    expect(modal[0]).toContain('Gagal impor');
    expect(modal[0]).not.toContain('Tersimpan');
  });

  test('tag gabungan "import-error error" dikenali sebagai error (bukan token pertama)', () => {
    const modal = renderMessages([['import-error error', 'Impor gagal']]);
    expect(visible()).toHaveLength(0);
    expect(modal).toHaveLength(1);
    expect(document.getElementById('messagesModalTitle').textContent).toContain('Error');
  });

  test('escape dari |escapejs didekode dan tetap dirender sebagai teks', () => {
    renderMessages([['success', 'Proyek \\u0022A\\u002D1\\u0022 \\u003Cb\\u003Ex\\u003C/b\\u003E tersimpan']]);
    const text = visible()[0].textContent;
    expect(text).toContain('Proyek "A-1" <b>x</b> tersimpan');
    expect(visible()[0].querySelector('b')).toBeNull();
  });

  test('tanpa DP.toast semua pesan tetap tampil di modal', () => {
    document.body.innerHTML = '';
    delete window.DP;
    document.body.insertAdjacentHTML('beforeend', `
      <div id="messagesModal"><div id="messagesModalHeader"></div>
        <h5 id="messagesModalTitle"></h5><div id="messagesModalBody"></div></div>
      <div id="django-messages-data"><div class="message-item" data-tags="success" data-message="Tersimpan"></div></div>`);
    const shown = [];
    window.bootstrap = { Modal: class { show() { shown.push(document.getElementById('messagesModalBody').textContent); } } };
    // eslint-disable-next-line no-new-func
    new Function(MESSAGES_SRC)();
    expect(shown).toHaveLength(1);
    expect(shown[0]).toContain('Tersimpan');
  });
});

describe('pemanggil toast (T-3)', () => {
  const app = readFileSync(resolve(JS_DIR, 'src', 'jadwal_kegiatan_app.js'), 'utf-8');

  test('Jadwal tidak lagi mengirim objek {duration, position} ke Toast', () => {
    expect(app).not.toMatch(/Toast\.\w+\([^;]*\{\s*duration/);
    expect(app).not.toMatch(/position:\s*'top-right'/);
  });

  test('simpan Jadwal tidak menambah toast kedua di atas SaveHandler (T-F3)', () => {
    expect(app).not.toContain("Toast.success('Perubahan berhasil disimpan')");
    expect(app).not.toContain("'Perubahan gagal disimpan'");
  });

  test('toast proses validasi bundle Template AHSP ditutup (T-F4)', () => {
    const src = readFileSync(resolve(JS_DIR, 'template_ahsp.js'), 'utf-8');
    expect(src).not.toMatch(/toast\(loadingMsg,\s*'info',\s*0\)/);
    expect(src).toContain('DP.toast.dismiss(loadingToast)');
  });
});
