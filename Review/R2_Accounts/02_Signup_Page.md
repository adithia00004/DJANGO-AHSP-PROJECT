# R2.2 - Review Signup Page

**Status:** `[x]` SELESAI DIREVIEW - PASS (non-responsive)
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/accounts/signup/` |
| View | `allauth.account.views.SignupView` |
| Template | `templates/account/signup.html` |
| Auth Required | Tidak (public) |
| Konfigurasi | `ACCOUNT_SIGNUP_FIELDS`, `ACCOUNT_EMAIL_VERIFICATION` |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Signup data valid | User dibuat | `[x]` | PASS - user terbuat + redirect 302 |
| TC-2 | CSRF protection | Token ada | `[x]` | PASS |
| TC-3 | Link ke login | Navigasi benar | `[x]` | PASS |
| TC-4 | Email duplikat | Ditolak aman tanpa account enumeration | `[x]` | PASS - user duplikat tidak terbuat, pesan dinetralkan |
| TC-5 | Password validation | Password lemah ditolak | `[x]` | PASS - allauth + Django validators aktif |
| TC-6 | Status trial pasca-signup | Konsisten dengan entitlement write access | `[x]` | PASS - `is_subscription_active=False` selaras dengan `can_edit=False` hingga trial aktif |
| TC-7 | Responsive mobile | Form usable | `[~]` | Perlu validasi visual manual |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | State trial pasca-signup kini konsisten: trial yang belum aktif tidak lagi mendapat write access. | `subscriptions/entitlements.py:141` | Runtime 2026-02-17: signup user -> `is_subscription_active=False`, `can_edit=False`, decision `SUBSCRIPTION_EXPIRED`. |
| F-2 | **RESOLVED (was MEDIUM)** | Pesan duplicate email dinetralkan melalui adapter error message override agar tidak mengungkap status registrasi email secara eksplisit. | `config/adapters.py:14` | Runtime 2026-02-17: duplicate signup ditolak (`users_with_email` tetap 1), pesan generic muncul. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Tegaskan lifecycle trial: jangan izinkan write access untuk `TRIAL` yang `trial_end_date` null; enforce via entitlement guard atau set state awal ke `EXPIRED` sampai verifikasi sukses | P0 | Medium | F-1 (`[DONE]`) |
| REC-2 | Aktifkan mode pencegahan enumeration yang lebih ketat (`ACCOUNT_PREVENT_ENUMERATION = "strict"`) atau samakan pesan error agar netral | P1 | Low | F-2 (`[DONE]` via generic adapter message, tanpa duplikasi user) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Audit runtime signup flow (valid, duplicate email, state trial pasca signup) | - | DONE |
| 2 | 2026-02-17 | Normalisasi entitlement untuk trial/pro non-aktif agar tidak memperoleh write access | - | DONE |
| 3 | 2026-02-17 | Hardening duplicate-email message via `AccountAdapter.error_messages['email_taken']` | - | DONE |

---

## Checklist Sign-off

- [x] Fungsional dasar signup OK
- [x] Keamanan OK (duplicate signup tidak mengungkap status email eksplisit)
- [x] Subscription state consistency OK
- [ ] Responsive OK (manual check)
- [ ] Reviewer sign-off
