# 38 — Rencana Eksekusi: Perubahan Tanggal Proyek dengan Progress

| | |
|---|---|
| Status | Siap dieksekusi setelah §5 disetujui |
| Tanggal | 2026-08-24 |
| Latar belakang | Doc 37 (analisis lengkap, temuan T-01…T-06 dan G-1…G-6) |
| Dokumen ini | Hanya bagian yang akan dikerjakan. Sisanya tetap backlog di doc 37 |

---

## 1. Sasaran

Menutup tiga hal, tidak lebih:

1. **Mass edit menghapus seluruh progress tanpa pemberitahuan** saat tanggal mulai diubah.
   Satu-satunya kehilangan data nyata.
2. **Tanggal mulai terkunci total** begitu ada progress. Jalan buntu tanpa opsi.
3. **Sisa baris di luar jendela tidak pernah dibereskan**, membuat jadwal basi setelah perubahan
   yang sukses.

## 2. Batas lingkup

**Dikerjakan:** mesin resolusi 3 opsi, penghentian penghapusan senyap di mass edit, pembersihan baris
di luar jendela, audit yang dapat dipulihkan, dialog pilihan di form edit project, dan tombol Jadwal
menjadi perbaikan terpandu.

**TIDAK dikerjakan di sini** (tetap di backlog doc 37): jalur Django admin (G-1), duplikat project
(G-2), perubahan batas minggu (G-3), tahapan manual (G-4), bug `month_number` monthly, cache chart
regenerate (T-05).

**Ditunda dengan sengaja:** proyek yang sudah punya **realisasi** pada minggu terdampak tetap
ditolak seperti hari ini. Membuka kasus itu memerlukan pertanyaan niat "koreksi vs pergeseran"
(doc 37 §4.1) yang belum diputuskan. Kasus **rencana-saja** — mayoritas, karena terjadi di tahap
perencanaan — sudah terbuka penuh di rencana ini.

## 3. Tiga opsi yang ditawarkan

| Opsi | Arti bagi user | Total progress |
|---|---|---|
| **Pertahankan urutan minggu** | "Minggu ke-1 tetap minggu ke-1, hanya tanggalnya yang berubah" | Utuh |
| **Padatkan ke minggu batas** | "Progress yang jatuh di luar jadwal baru ditumpuk ke minggu pertama (atau terakhir)" | Utuh, distribusi berubah |
| **Hapus yang di luar jadwal baru** | "Progress di luar jendela dibuang; yang di dalam tidak tersentuh" | Berkurang, disengaja |

Contoh konkret, proyek mulai 01/01/2026 digeser ke 01/03/2026, rencana W1=10%, W2=15%, W9=20%
(W9 sudah berada di dalam jendela baru):

| | W1 baru (01–07/03) | W2 baru (08–14/03) | Minggu berisi 20% |
|---|---|---|---|
| Pertahankan urutan | 10% | 15% | tetap di urutan ke-9 |
| Padatkan ke batas | 25% (10+15) | 0% | tetap |
| Hapus yang di luar | 0% | 0% | tetap |

Batas kuantitas aman: total per pekerjaan sudah dibatasi ≤ 100%, dan memindahkan nilai tidak menambah
total — jadi tidak ada opsi yang bisa melanggarnya (doc 37 §4.5).

---

## 4. Tahapan

### Fase 1 — Mesin resolusi (backend, tanpa UI)

Fase ini menutup sasaran 1, 2, dan 3. Bisa dites penuh tanpa menyentuh tampilan.

| Langkah | Isi | Gate |
|---|---|---|
| **1.1** | Test yang mengunci perilaku **sekarang** sebelum apa pun diubah (mass edit menghapus, tanggal selesai tidak memicu rebuild, tanggal mulai ditolak) | Test baru + 11 test `tests_timeline_crud_hardening.py` hijau |
| **1.2** | Tiga resolusi di `timeline_utils.py` + pembersihan baris di luar jendela + snapshot audit lengkap + pola dua fase untuk UNIQUE `(pekerjaan, week_number)` | Matriks §6 hijau; `timeline_stale == false` dan jumlah kolom == jumlah minggu jendela baru setelah **setiap** commit sukses; 11 test lama hijau **tanpa dimodifikasi** |
| **1.3** | `views_mass_edit.py` berhenti memanggil `reset_project_progress`; memakai analisis dampak untuk memisahkan project aman vs perlu-keputusan; tangani perubahan tanggal selesai | Test 1.1 dibalik jadi test perilaku baru; tidak ada progress terhapus tanpa resolusi eksplisit |

### Fase 2 — Dialog pilihan

| Langkah | Isi | Gate |
|---|---|---|
| **2.1** | Perluas kotak dampak di `project_form.html` menjadi dialog pilihan: jendela lama→baru, jumlah minggu lama→baru, tabel per-minggu nilai lama→baru, total sebelum→sesudah, opsi yang sah saja | Test view: POST tanpa resolusi → dialog ter-render; POST dengan resolusi → tersimpan |
| **2.2** | Mass edit menampilkan ringkasan agregat ("3 project aman, 1 perlu keputusan") dan mengarahkan yang tidak aman ke edit tunggal | Test: project tidak aman tidak ikut tersimpan |

### Fase 3 — Tombol Jadwal

| Langkah | Isi | Gate |
|---|---|---|
| **3.1** | Halaman Jadwal membaca `readiness.timeline_stale`. Tombol keluar dari toolbar utama, menjadi alert kondisional yang membuka dialog yang sama | Test: alert tidak muncul saat `timeline_stale=false` |

**Urutan wajib 1 → 2 → 3.** Fase 1 berdiri sendiri dan sudah bernilai: penghapusan senyap berhenti
di situ, bahkan sebelum ada UI baru.

---

## 5. Yang perlu disetujui sebelum mulai

| # | Keputusan | Rekomendasi |
|---|---|---|
| **A** | Tiga opsi di §3 sudah cukup untuk rilis pertama | Ya; opsi keempat (padatkan proporsional) menyusul bila terbukti perlu |
| **B** | Default saat tanggal mulai bergeser | "Pertahankan urutan minggu" — satu-satunya yang tidak kehilangan apa pun |
| **C** | Mass edit: project yang perlu keputusan **tidak ikut tersimpan** dan diarahkan ke edit tunggal | Ya; jauh lebih murah daripada membangun dialog di dalam grid |
| **D** | Kasus dengan realisasi tetap ditolak di rilis ini | Ya; dibuka setelah pertanyaan niat diputuskan |

---

## 6. Skenario dari sisi user

Kolom terakhir menandai apa yang berubah dibanding hari ini.

### 6.1 Edit project satu per satu

| # | Yang user lakukan | Yang user lihat setelah rencana ini | Berubah? |
|---|---|---|---|
| 1 | Perpanjang tanggal selesai | Tersimpan langsung. Progress utuh, minggu baru muncul kosong | Sama |
| 2 | Perpendek tanggal selesai, minggu terbuang kosong | Tersimpan langsung. Jadwal langsung rapi, tidak ada kolom sisa | **Baru** — sekarang kolom sisa tertinggal |
| 3 | Perpendek tanggal selesai, minggu terbuang berisi **rencana** | Dialog: *Padatkan ke minggu terakhir* / *Hapus yang di luar* / *Batalkan*, lengkap dengan tabel nilai lama→baru | **Baru** — sekarang hanya ada "Potong Planned Progress" |
| 4 | Perpendek tanggal selesai, minggu terbuang berisi **realisasi** | Ditolak, menyebut minggu mana yang bermasalah dan apa yang harus dibereskan dulu | Lebih jelas, tetap ditolak |
| 5 | **Geser tanggal mulai, durasi tetap, hanya rencana** | Dialog tiga opsi, default *Pertahankan urutan minggu* — nilai tidak ada yang hilang | **Baru** — sekarang buntu total |
| 6 | Geser tanggal mulai, durasi berubah, hanya rencana | Dialog tiga opsi | **Baru** — sekarang buntu total |
| 7 | Geser tanggal mulai, ada realisasi di mana pun | Ditolak, dengan penjelasan alasannya | Lebih jelas, tetap ditolak |
| 8 | Salah pilih opsi | Nilai lama tersimpan lengkap di audit dan dapat dipulihkan manual | **Baru** — sekarang hanya nilai rencana lama |

### 6.2 Mass edit

| # | Yang user lakukan | Yang user lihat setelah rencana ini | Berubah? |
|---|---|---|---|
| 9 | Ubah tanggal mulai beberapa project, semua aman | Semua tersimpan, jadwal ikut dibangun ulang | **Baru** — sekarang seluruh progress terhapus |
| 10 | Ubah tanggal mulai, sebagian perlu keputusan | Yang aman tersimpan; yang perlu keputusan dilaporkan per nama dan **tidak** tersimpan, dengan tautan ke edit tunggal | **Baru** — sekarang terhapus diam-diam |
| 11 | Ubah tanggal selesai | Jadwal ikut dibangun ulang | **Baru** — sekarang tidak terjadi apa-apa |

### 6.3 Halaman Jadwal

| # | Yang user lakukan | Yang user lihat setelah rencana ini | Berubah? |
|---|---|---|---|
| 12 | Membuka Jadwal setelah perubahan yang sukses | Jumlah kolom sesuai jendela baru, tidak ada peringatan | **Baru** — sekarang muncul kolom sisa dan status basi |
| 13 | Membuka Jadwal saat struktur memang basi | Alert dengan tombol perbaikan yang membuka dialog dampak | **Baru** — sekarang tombol selalu ada dan langsung memutasi |
| 14 | Membuka Jadwal saat semuanya normal | Tidak ada tombol perbaikan sama sekali | **Baru** |
| 15 | Punya tab Jadwal terbuka saat tanggal diubah di tab lain | Simpan berikutnya ditolak: "Struktur jadwal sudah berubah. Muat ulang halaman" | Sama, tapi kini juga berlaku untuk perubahan lewat form |

---

## 7. Risiko

| Risiko | Mitigasi |
|---|---|
| Merusak jalur edit tunggal yang sudah matang | Langkah 1.2 mensyaratkan 11 test lama hijau **tanpa dimodifikasi** |
| Pergeseran menabrak UNIQUE `(pekerjaan, week_number)` | Pola dua fase dalam satu transaksi, seperti `rollback_parameters_from_opaque` |
| Proyek besar lambat saat update massal | `bulk_update`; ukur pada proyek terbesar sebelum 1.3 ditutup |
| User salah memilih opsi | Dialog wajib menampilkan tabel nilai lama→baru dan total; audit menyimpan snapshot penuh |

**Rollback:** setiap langkah satu commit. Langkah 1.2 murni aditif. Langkah 1.3 yang mengubah
perilaku destruktif — bila bermasalah, revert 1.3 saja tanpa menyentuh mesinnya.
