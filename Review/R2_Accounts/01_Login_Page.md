# R2.1 - Review Login Page

**Status:** `[x]` SELESAI DIREVIEW - PASS (non-responsive)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/accounts/login/` |
| View | `allauth.account.views.LoginView` |
| Template | `templates/account/login.html` |
| Base Template | `templates/base.html` |
| Auth Required | Tidak (public) |
| Redirect After | `AccountAdapter` (`next` valid -> `next`, default -> dashboard/admin portal) |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Login email + password valid | Redirect sukses | `[x]` | PASS - redirect ke `/dashboard/` |
| TC-2 | Password salah | Error generik | `[x]` | PASS - pesan generik tampil |
| TC-3 | Email tidak terdaftar | Error generik tanpa leak | `[x]` | PASS - pesan sama dengan password salah |
| TC-4 | CSRF token di form | Token ada | `[x]` | PASS - `{% csrf_token %}` ada |
| TC-5 | Brute force throttling | Dibatasi setelah beberapa attempt | `[x]` | PASS - rate-limit terdeteksi di attempt ke-6 |
| TC-6 | Link "Lupa Password" | Navigasi ke reset password | `[x]` | PASS - link tersedia via crispy help text |
| TC-7 | Link "Daftar" | Navigasi ke signup | `[x]` | PASS - `{% url 'account_signup' %}` aktif |
| TC-8 | Flow `next` parameter dari `/admin/login/` | Redirect tetap ke target `next` | `[x]` | PASS - hidden `next` field aktif; submit login mengarah ke target `next` |
| TC-9 | Responsive mobile | Form usable | `[~]` | Perlu validasi visual manual |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was MEDIUM)** | Flow `next` redirect kini terjaga melalui hidden redirect field pada form login. | `templates/account/login.html:29` | Runtime check 2026-02-17: `name="next" value="/admin/"` ada; post login dengan `next=/admin/` redirect ke `/admin/`. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Tambahkan hidden redirect field allauth di form login: `{% if redirect_field_value %}<input type="hidden" name="{{ redirect_field_name }}" value="{{ redirect_field_value }}" />{% endif %}` | P0 | Low (10-15 min) | F-1 (`[DONE]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit runtime login flow (valid/invalid/rate-limit/next redirect) | - | DONE |
| 2 | 2026-02-17 | Implementasi hidden redirect field `next` pada login form + regression test | - | DONE |

---

## Checklist Sign-off

- [x] Fungsional inti login OK
- [x] Keamanan dasar OK (CSRF + brute-force + generic error)
- [x] UX redirect flow OK (`next` preserved)
- [ ] Responsive OK (butuh manual check)
- [ ] Reviewer sign-off
