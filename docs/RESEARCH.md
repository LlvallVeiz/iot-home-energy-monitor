# Riset — iot-home-energy-monitor

## 1. Model beban rumah tangga (bottom-up, resolusi 1 menit)

Simulator ini memakai pendekatan *bottom-up*: daya total rumah tangga
adalah jumlah daya tiap alat pada tiap menit. Setiap alat punya tiga
parameter: daya saat menyala (`power_w`), jendela waktu pemakaian
(`windows`), dan duty cycle (`duty`) — fraksi menit di dalam jendela
saat alat benar-benar menyala. Duty cycle memodelkan siklus
hidup-mati kompresor/termostat (kulkas, AC, dispenser) dan pemakaian
sebentar-sebentar (pompa air). Keputusan menyala/mati tiap menit
diambil dari RNG ber-seed sehingga simulasi dapat direproduksi persis.

Pendekatan ini adalah bentuk sederhana dari pemodelan profil beban
yang dipakai dalam studi perencanaan energi rumah tangga; bedanya,
proyek ini tidak mengklaim kalibrasi terhadap pengukuran meteran
nyata — profilnya adalah profil tipikal yang transparan dan dapat
diubah lewat file JSON (`data/profiles/`).

### Daya alat acuan

| Alat | Daya model | Acuan |
| --- | --- | --- |
| Kulkas 1 pintu | 150 W, duty 40% | US DOE: kulkas ukuran penuh ~150 W, ~1,2 kWh/hari |
| AC split 1 PK | 800 W, duty 70% malam | AC jendela 1 ruangan ~650 W; AC 1 PK Indonesia umumnya 700–900 W |
| Rice cooker 1,8 L | 400 W masak; 40 W hangat | Rice cooker 5,5-cup Zojirushi 680 W; 10-cup 1.000 W; rentang umum 350–700 W |
| Mesin cuci top-load | 400 W | US DOE: mesin cuci ~500 W |
| TV LED | 80–100 W | TV LED ukuran 24–32 inci |
| Pompa air | 200–250 W | Pompa sumur dangkal rumah tangga |
| Lampu LED | 12 W/titik | Lampu LED rumah tangga umum |
| Kipas angin | 50 W/unit | Kipas angin berdiri umum |
| Dispenser | 250–300 W | Elemen pemanas dispenser |

Verifikasi internal: energi harian ekspektasi profil default
(dihitung dari daya × duty × durasi window) adalah 9,51 kWh/hari;
simulasi 7 hari seed 42 menghasilkan 9,38 kWh/hari — selisih 1,4%,
sesuai dengan variasi acak binomial. Kulkas simulasi 7 hari tepat
10,08 kWh = 7 × 1,44 kWh (ekspektasi), dan AC 31,71 kWh vs
ekspektasi 31,36 kWh (selisih 1,1%).

## 2. Tarif listrik PLN rumah tangga (Triwulan IV 2026)

Landasan hukum: **Peraturan Menteri ESDM Nomor 7 Tahun 2024**
tentang Tarif Tenaga Listrik yang Disediakan oleh PT PLN (Persero).
Tarif pelanggan nonsubsidi ditinjau tiap triwulan oleh Kementerian
ESDM berdasarkan kurs rupiah, ICP (Indonesian Crude Price), inflasi,
dan HBA (harga batu bara acuan). Penetapan Triwulan IV 2026
(1 Oktober–31 Desember 2026) diumumkan Menteri ESDM Bahlil Lahadalia
pada 30 September 2026 dan **tidak menaikkan tarif** dibanding
Triwulan III 2026.

### Tabel tarif rumah tangga yang dipakai (Rp/kWh)

| Golongan | Daya | Tarif |
| --- | --- | --- |
| R-1/TR subsidi | 450 VA | 415,00 |
| R-1/TR subsidi | 900 VA | 605,00 |
| R-1/TR RTM (nonsubsidi) | 900 VA | 1.352,00 |
| R-1/TR | 1.300 VA | 1.444,70 |
| R-1/TR | 2.200 VA | 1.444,70 |
| R-2/TR | 3.500–5.500 VA | 1.699,53 |
| R-3/TR | 6.600 VA ke atas | 1.699,53 |

### Fakta penting: tarifnya FLAT, bukan blok bertingkat

Tarif rumah tangga PLN saat ini bersifat **flat per kWh per
golongan** — satu angka per kWh untuk seluruh pemakaian dalam satu
golongan. Sistem blok bertingkat progresif (Blok I/II/III) sudah
tidak berlaku untuk rumah tangga. Karena itu modul `tariffs.py`
menghitung tagihan sebagai `kWh × tarif golongan + PPJ + biaya
admin`, dan "bertingkat" di proyek ini merujuk pada tangga
golongan daya (makin besar daya terpasang, makin tinggi tarif/kWh).
Siapa pun yang menerapkan tarif blok lama ke tagihan 2026 akan
mendapat angka yang salah — kekeliruan ini sengaja dihindari di sini.

### PPJ dan token

- **PPJ (Pajak Penerangan Jalan, kini PBJT tenaga listrik)** adalah
  pajak daerah yang besarnya ditetapkan pemerintah kabupaten/kota dan
  berbeda-beda tiap daerah. Nilai 3% dipakai sebagai default karena
  dipakai dalam contoh hitung token yang diberitakan; ganti dengan
  persentase daerah Anda (`--ppj`).
- **Rumus token prabayar** (dari contoh yang diberitakan):
  `kWh = (nominal − biaya admin − PPJ) / tarif`, dengan
  `PPJ = persen PPJ × nominal`. Contoh terverifikasi: token Rp50.000
  di golongan 1.300 VA dengan PPJ 3% menghasilkan
  (50.000 − 1.500) / 1.444,70 = **33,57 kWh** — angka ini cocok
  dengan pemberitaan dan dipakai sebagai tes regresi.

## 3. Analisis beban

- **Energi**: 1 menit pada P watt = P/60.000 kWh.
- **Faktor beban** = daya rata-rata / daya puncak (0..1). Profil
  default: 0,322 — beban terkonsentrasi di malam hari (AC), wajar
  untuk rumah tangga ber-AC.
- **Lonjakan daya**: menit berurutan di atas 80% daya terpasang
  (1.040 W untuk 1.300 VA), dihitung hanya bila bertahan ≥ 5 menit
  agar kombinasi alat yang kebetulan menyala 1 menit tidak dihitung
  sebagai kejadian. Dalam simulasi 7 hari: 11 kejadian, semuanya
  sekitar pukul 21:30 (AC + TV + lampu + kulkas + kipas bersamaan),
  puncak 1.215 W — masih di bawah 1.300 VA sehingga MCB tidak trip,
  tapi nyaris.
- **Anomali harian**: z-score konsumsi harian terhadap rata-rata dan
  simpangan baku periode simulasi (ambang |z| > 2, minimal 3 hari
  data). Dalam contoh 7 hari: 0 anomali — konsumsi harian stabil
  9,13–9,69 kWh.

## 4. Penghematan energi

- **Termostat AC**: US DOE menyatakan penghematan hingga 10% per
  tahun untuk pemanasan/pendinginan dengan menaikkan setelan
  termostat 7–10°F selama 8 jam sehari dari setelan normal. Proyek
  ini memakai angka 10% sebagai skenario untuk rekomendasi AC —
  estimasi, bukan janji, dan dihitung dari pangsa AC hasil simulasi.
- **Mode hangat rice cooker**: elemen pemanas 40 W yang hidup-mati
  sepanjang hari memakai ~0,28 kWh/hari (3,0% total) hanya untuk
  menjaga nasi hangat; mencabut setelah masak menghemat sebagian
  besar angka ini.
- **Beban siaga (standby)**: 5 W terus-menerus = 0,12 kWh/hari
  (1,3% total). Kecil per hari, tetapi mengalir 365 hari setahun.

## 5. Keterbatasan

- Profil pemakaian adalah **tipikal, bukan pengukuran**: angka daya
  dan jadwal berasal dari acuan umum di atas, bukan dari meteran di
  satu rumah nyata. Untuk memakai data sendiri, ganti
  `data/profiles/*.json` atau impor CSV dari smart meter (format
  kolom sama dengan output `simulate`).
- RNG menit-per-menit tidak memodelkan arus start (lonjakan sesaat
  saat kompresor menyala, bisa 5–7× daya jalan) — daya puncak di sini
  adalah daya jalan, bukan arus start.
- Tarif bisa berubah tiap triwulan; perbarui
  `data/tariffs/pln_q4_2026.json` bila ESDM menetapkan tarif baru.
- PPJ 3% adalah asumsi; tagihan resmi memakai persentase daerah dan
  bisa memuat komponen lain (biaya admin, PPN untuk golongan
  tertentu).

## References

1. Kementerian ESDM — Peraturan Menteri ESDM Nomor 7 Tahun 2024
   tentang Tarif Tenaga Listrik yang Disediakan oleh PT PLN (Persero).
   https://www.esdm.go.id/
2. FORTUNE Indonesia — "Tarif Listrik Terbaru November 2026, Benarkah
   Ada Kenaikan?", 2 Nov 2026.
   https://www.fortuneidn.com/news/tarif-listrik-terbaru-november-2026-d7w02-00-lflgw-x8t35n
3. Topik.id — "Tarif Listrik November 2026 Naik atau Tidak? Ini
   Keputusan ESDM dan Daftar Harga PLN".
   https://www.topik.id/tarif-listrik-november-2026-naik-atau-tidak-ini-keputusan-esdm-dan-daftar-harga-pln
4. Mughu.id — "Tarif Listrik Naik? Cek Tarif November 2026 di PLN Mobile".
   https://www.mughu.id/blog/tarif-listrik-naik-cek-pln-mobile
5. Lensa Hukum — "Token Listrik Rp 50.000 Menghasilkan 33,57 kWh pada
   19 Oktober 2026". https://lensahukum.co.id/token-listrik-50-ribu-19-oktober-2026
6. TarifHarga.com — "Cara Menghitung Tagihan Listrik PLN (Pascabayar &
   Token) + Contoh Lengkap".
   https://www.tarifharga.com/2026/10/cara-menghitung-tagihan-listrik-pln.html
7. U.S. Department of Energy — "Programmable Thermostats" (hemat
   hingga 10%/tahun dengan setback termostat 7–10°F selama 8 jam/hari).
   https://www.energy.gov/energysaver/thermostats
8. U.S. Department of Energy — "Estimating Appliance and Home
   Electronic Energy Use" (daya acuan kulkas, mesin cuci, dll.).
   https://www.energy.gov/energysaver/estimating-appliance-and-home-electronic-energy-use
9. Paravolta — "Appliance Wattage Chart" (2026), merangkum angka US DOE
   dan spesifikasi pabrikan (termasuk rice cooker Zojirushi).
   https://paravolta.com/guides/appliance-wattage-chart/
10. PT PLN (Persero) — portal resmi. https://web.pln.co.id/
