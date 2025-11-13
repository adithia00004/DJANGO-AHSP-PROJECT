# Workflow 3 Pages – User-side Flow & Safeguards

_Dokumen ini merangkum bagaimana pengguna berinteraksi dengan Workflow 3 Pages (Template AHSP → Harga Items → Rincian AHSP), opsi tindakan yang tersedia pada setiap tahap, syarat & kondisi yang perlu dipenuhi, serta mekanisme error handling yang disediakan sistem._

## 1. Gambaran Umum

1. **Template AHSP (Input Komponen)** – User menginput komponen TK/BHN/ALT atau bundle LAIN untuk setiap pekerjaan **source_type=CUSTOM** kemudian menyimpan manual agar sistem melakukan ekspansi dan invalidasi dependensi.【F:detail_project/WORKFLOW_3_PAGES.md†L17-L97】【F:detail_project/WORKFLOW_3_PAGES.md†L249-L333】
2. **Harga Items (Penetapan Harga)** – User memfilter daftar komponen hasil ekspansi, menetapkan harga satuan dan global profit (BUK), lalu menyimpan secara manual dengan validasi angka serta optimistic locking.【F:detail_project/WORKFLOW_3_PAGES.md†L98-L175】
3. **Rincian AHSP (Review & Recap)** – User meninjau komponen lengkap dengan harga, mengecek kalkulasi total, menerapkan override BUK per pekerjaan bila diperlukan, dan mengekspor rekap ketika siap.【F:detail_project/WORKFLOW_3_PAGES.md†L176-L247】

Setiap halaman memakai tombol **Simpan** manual, menerapkan **optimistic locking** untuk konflik simultan, serta menjaga konsistensi dual-storage (raw input, expanded items, pricing master).【F:detail_project/WORKFLOW_3_PAGES.md†L32-L95】

## 2. Tahap 1 – Template AHSP

| Aspek | Detail User Flow | Requirements / Validasi | Error Handling |
| --- | --- | --- | --- |
| Pilih pekerjaan | Sidebar menampilkan tiga state: (1) REFERENSI → view only; (2) REFERENSI_MODIFIED → Segment A–C aktif untuk edit dasar; (3) CUSTOM → Segment A–D aktif dan bundle bisa ditambah.| REFERENSI_MODIFIED mengikuti komponen referensi yang sudah dimuat; CUSTOM boleh membuat/menyunting semua segmen termasuk bundle.| - REFERENSI: tombol edit/segment disabled dengan tooltip "Data referensi hanya dapat dibaca".<br>- REFERENSI_MODIFIED: Segment D terkunci dan snackbar muncul bila user mencoba membukanya.<br>- CUSTOM: guard tetap memeriksa circular dan batas loop (maks 3).【F:detail_project/WORKFLOW_3_PAGES.md†L249-L333】|
| Input komponen langsung | User memasukkan TK/BHN/ALT dengan kode unik dan koefisien per pekerjaan.| Kode harus unik per pekerjaan dan memenuhi kategori valid.| Server-side validation menolak kode duplikat / kategori salah, menampilkan pesan form error.【F:detail_project/WORKFLOW_3_PAGES.md†L46-L79】|
| Input bundle (LAIN) | User memilih referensi pekerjaan proyek (`ref_kind='job'`) atau AHSP master (`ref_kind='ahsp'`) melalui autocomplete.| Target harus memiliki komponen, tidak boleh circular, dan hanya bisa ditambahkan ke pekerjaan CUSTOM.| - Empty bundle: API menolak dan menampilkan error `"Target tidak punya komponen"`.<br>- Circular reference: util `check_circular_dependency_pekerjaan` memblokir penyimpanan dan menampilkan peringatan.【F:detail_project/WORKFLOW_3_PAGES.md†L50-L97】【F:detail_project/WORKFLOW_3_PAGES.md†L334-L414】|
| Simpan manual | User klik **Simpan** setelah selesai menginput komponen/bundle.| Semua input valid, tidak ada konflik edit.| - **Optimistic locking**: jika ada konflik, dialog menawarkan _Muat Ulang_ atau _Timpa_.<br>- Jika valid: sistem menyimpan raw input, ekspansi ulang, membuat harga baru (NULL), cascade ke pekerjaan dependan, dan menampilkan toast sukses.【F:detail_project/WORKFLOW_3_PAGES.md†L60-L97】|

## 3. Tahap 2 – Harga Items

| Aspek | Detail User Flow | Requirements / Validasi | Error Handling |
| --- | --- | --- | --- |
| Filter & review | User memfilter berdasarkan kategori atau kata kunci dan hanya melihat komponen TK/BHN/ALT hasil ekspansi (bundle tidak muncul).| Data diambil dari `DetailAHSPExpanded` sehingga daftar selalu sinkron dengan input template.| Jika ekspansi gagal, daftar kosong dan banner error menuntun user kembali ke Template AHSP.【F:detail_project/WORKFLOW_3_PAGES.md†L98-L140】|
| Input harga | User mengisi harga satuan dengan masker angka; NULL ditampilkan sebagai "0.00".| Nilai harus non-negatif, maksimal 2 desimal, dan kosong otomatis menjadi 0 (tetap disimpan sebagai NULL bila user tidak mengetik).| - Validasi client/server menolak format salah.<br>- Sistem mempertahankan NULL di DB sehingga audit dapat membedakan "belum diisi" vs "nol".【F:detail_project/WORKFLOW_3_PAGES.md†L118-L152】|
| Global BUK | User dapat mengubah `ProjectPricing.markup_percent` langsung pada halaman yang sama.| Input 0–100% dengan 2 desimal.| Validasi menolak nilai di luar rentang dan menampilkan pesan inline.【F:detail_project/WORKFLOW_3_PAGES.md†L152-L165】|
| Simpan manual | User klik **Simpan** setelah seluruh harga/BUK diisi.| Semua angka valid dan tidak ada konflik edit.| - **Optimistic locking**: konflik menampilkan opsi _Muat Ulang_ atau _Timpa_.<br>- Jika sukses: HargaItemProject diperbarui, konversi satuan disimpan, cache rekap di-invalidate, toast sukses muncul.【F:detail_project/WORKFLOW_3_PAGES.md†L140-L175】|

## 4. Tahap 3 – Rincian AHSP

| Aspek | Detail User Flow | Requirements / Validasi | Error Handling |
| --- | --- | --- | --- |
| Navigasi & review | User memilih pekerjaan, melihat komponen lengkap dengan badge bundle, serta memeriksa subtotal TK/BHN/ALT.| Data merupakan join `DetailAHSPExpanded` + `HargaItemProject`; harga 0.00 menandakan NULL (belum diisi).| Jika harga masih NULL, baris diberi indikator visual sehingga user tahu harus kembali ke Harga Items.【F:detail_project/WORKFLOW_3_PAGES.md†L176-L217】|
| Override BUK | User membuka dialog "Override BUK" untuk mengatur margin khusus per pekerjaan atau reset ke default.| Nilai 0–100%, max 2 desimal; override disimpan di `Pekerjaan.markup_override_percent`.| Validasi angka menolak input ilegal dan menampilkan pesan; penyimpanan memicu invalidasi cache dan refresh chip indikator.【F:detail_project/WORKFLOW_3_PAGES.md†L209-L239】|
| Export RAB | Setelah semua total benar, user klik tombol export.| Semua harga/override telah diverifikasi.| Jika ada data belum lengkap, sistem meminta user melengkapi harga terlebih dahulu sebelum export sukses.【F:detail_project/WORKFLOW_3_PAGES.md†L239-L247】|

## 5. Opsi Khusus & Kondisi Penting

1. **Sumber Bundle** – User bebas memilih bundle dari pekerjaan proyek atau AHSP master, selama target sudah memiliki komponen dan bukan pekerjaan REF/REF_MODIFIED pada halaman Template AHSP.【F:detail_project/WORKFLOW_3_PAGES.md†L249-L333】
2. **Reuse Pekerjaan Custom** – "Pekerjaan berulang" berarti user membuat pekerjaan CUSTOM khusus untuk dijadikan bundle dan menggunakannya di banyak pekerjaan lain.【F:detail_project/WORKFLOW_3_PAGES.md†L333-L370】
3. **Hierarchical Multiply** – Koefisien bundle akan dikalikan secara hierarkis saat diekspansi, sehingga perubahan di pekerjaan sumber otomatis memengaruhi seluruh pekerjaan yang mereferensikannya.【F:detail_project/WORKFLOW_3_PAGES.md†L370-L414】
4. **Circular Guard** – Sebelum menyimpan bundle, sistem menjalankan `check_circular_dependency_pekerjaan`; bila terdeteksi siklus, penyimpanan dibatalkan dengan pesan error eksplisit.【F:detail_project/WORKFLOW_3_PAGES.md†L390-L414】

## 6. Ringkasan Error Handling

| Kondisi | Deteksi | Respons Sistem | Dampak ke User |
| --- | --- | --- | --- |
| Bundle target tanpa komponen | Validasi server ketika memilih referensi | API mengembalikan HTTP 400 dengan pesan "Target belum memiliki komponen" | User diminta melengkapi pekerjaan target dulu sebelum menyimpan bundle.【F:detail_project/WORKFLOW_3_PAGES.md†L50-L97】|
| Circular dependency antar bundle | Utility `check_circular_dependency_pekerjaan` sebelum save | Penyimpanan diblokir, dialog error menjelaskan siklus | User harus mengganti referensi bundle untuk menghilangkan siklus.【F:detail_project/WORKFLOW_3_PAGES.md†L370-L414】|
| Konflik edit simultan | Optimistic locking pada Template AHSP & Harga Items | Dialog menawarkan "Muat Ulang" (ambil perubahan terbaru) atau "Timpa" (paksa simpan) | User memilih strategi sesuai kebutuhan; default aman adalah Muat Ulang.【F:detail_project/WORKFLOW_3_PAGES.md†L60-L175】|
| Format harga tidak valid | Client mask + serializer validation | Form field di-highlight merah dengan pesan "Format salah/negatif" | User memperbaiki input sebelum bisa menyimpan.【F:detail_project/WORKFLOW_3_PAGES.md†L118-L175】|
| Override BUK invalid | Dialog validation 0–100% | Pesan error inline dan simpan dibatalkan | User mengoreksi angka sesuai batasan.【F:detail_project/WORKFLOW_3_PAGES.md†L209-L239】|
| Harga belum diisi tetapi user lanjut ke Rincian | Join menandai harga NULL sebagai 0.00 dan badge peringatan | Tidak ada kalkulasi ulang sampai harga diisi; user diarahkan kembali ke Harga Items | Menjamin total Rincian tidak memakai data kosong.【F:detail_project/WORKFLOW_3_PAGES.md†L176-L247】|

---

_Dokumen ini melengkapi `docs/WORKFLOW_3_PAGES_IMPLEMENTATION_AGENDA.md` dengan fokus pada pengalaman pengguna dan bagaimana sistem menangani opsi, prasyarat, serta error pada setiap tahap._

## 7. Respons Sistem Berdasarkan Source Type

| Source Type | Akses di Template AHSP | Dampak ke Harga Items & Rincian | Penanganan Error Khusus |
| --- | --- | --- | --- |
| **REFERENSI** | Benar-benar read-only. UI menonaktifkan semua kontrol input dan hanya memperlihatkan data yang diambil dari database referensi. | Harga Items dan Rincian hanya bisa melihat hasil ekspansi default tanpa opsi override atau edit. | Jika user memaksa edit (mis. lewat URL langsung), API mengembalikan HTTP 403 dengan pesan "Pekerjaan referensi tidak dapat diubah". |
| **REFERENSI_MODIFIED** | Segment A–C (TK/BHN/ALT) dapat diubah untuk menambah/menghapus/memodifikasi baris. Segment D selalu disable. | Harga Items memuat hasil ekspansi baru (tanpa bundle tambahan). Rincian AHSP menunjukkan label "Ref-Modified" agar audit tahu sumbernya. | Percobaan menambah bundle akan dipotong di server dengan error toast "Segment D hanya untuk pekerjaan Custom" dan perubahan dibatalkan. |
| **CUSTOM** | Semua segmen aktif termasuk Segment D (LAIN). User bebas membuat template baru atau memanfaatkan bundle dari pekerjaan lain/master. | Harga Items dan Rincian akan memperlihatkan hasil ekspansi penuh, termasuk efek loop hingga maksimum 3 level. | Saat user mencoba membuat loop >3 level, validator bundle menolak dengan error "Bundle depth limit tercapai"; circular detection juga dijalankan sebelum save. |

_Dengan tabel ini, dokumentasi Workflow 3 Pages kini merefleksikan garis besar rencana: REFERENSI read-only, REFERENSI_MODIFIED membuka kontrol terbatas pada segment dasar, dan CUSTOM memberi akses penuh termasuk Segment D beserta batasan loop tiga tingkat._
