# iot-home-energy-monitor

Simulator beban listrik rumah tangga, tarif PLN, analisis konsumsi,
dan dashboard web statis — sistem end-to-end dari profil pemakaian
sampai estimasi tagihan. Python murni (standard library saja, tanpa
dependensi runtime); Chart.js untuk dashboard dimuat dari CDN.

## Background

Tagihan listrik rumah tangga sering terasa seperti kotak hitam: angka
kWh di meteran tidak menjelaskan *alat apa* yang menghabiskannya dan
*kapan*. Proyek ini menjawabnya dengan simulasi bottom-up: tiap alat
dimodelkan dengan daya, jendela waktu pemakaian, dan duty cycle
(siklus hidup-mati kompresor/termostat), lalu disimulasikan per menit
selama N hari. Hasilnya dianalisis (konsumsi per alat, beban puncak,
lonjakan daya, anomali harian) dan ditagih dengan **tarif PLN resmi
Triwulan IV 2026** (1 Oktober–31 Desember 2026, Permen ESDM No. 7
Tahun 2024).

Satu fakta yang sering salah kaprah: tarif rumah tangga PLN saat ini
bersifat **flat per kWh per golongan**, bukan blok bertingkat
progresif. Tagihan = `kWh × tarif golongan + PPJ + biaya admin`.
Detail riset, sumber, dan verifikasi hitung tangan ada di
[`docs/RESEARCH.md`](docs/RESEARCH.md).

## Project structure

```
iot-home-energy-monitor/
├── src/iot_home_energy_monitor/
│   ├── appliances.py      # model alat + profil rumah tangga (JSON)
│   ├── simulator.py       # simulasi deret waktu, resolusi 1 menit
│   ├── storage.py         # baca/tulis CSV dan SQLite
│   ├── tariffs.py         # tarif PLN Q4 2026 + hitung tagihan/token
│   ├── analysis.py        # agregasi kWh, puncak, lonjakan, anomali
│   ├── recommendations.py # rekomendasi hemat berbasis data
│   ├── report.py          # laporan Markdown + JSON
│   ├── dashboard.py       # generator dashboard HTML + Chart.js
│   └── cli.py             # CLI: simulate / analyze / bill / dashboard
├── data/
│   ├── profiles/          # default_household (1300 VA), small_household (900 VA)
│   └── tariffs/           # pln_q4_2026.json (tarif resmi + metadata)
├── tests/                 # 74 tes pytest (hitung tangan + round-trip + CLI)
├── examples/              # output asli dari run beneran (7 hari)
│   ├── sim_7d.csv / sim_7d.sqlite
│   ├── report_7d.md / report_7d.json
│   ├── small_7d.csv / small_report_7d.md
│   └── dashboard/index.html
├── docs/RESEARCH.md
├── pyproject.toml
└── requirements.txt       # hanya pytest (dev); runtime tanpa dependensi
```

## Cara jalan

```bash
pip install -e .          # opsional; atau jalankan dengan PYTHONPATH=src
export PYTHONPATH=src

# 1. Simulasikan 7 hari (profil default, 1300 VA) ke CSV + SQLite
python -m iot_home_energy_monitor simulate --profile default_household \
  --days 7 --start 2026-11-10 --seed 42 \
  --csv examples/sim_7d.csv --sqlite examples/sim_7d.sqlite

# 2. Analisis -> laporan Markdown + JSON
python -m iot_home_energy_monitor analyze --input examples/sim_7d.csv \
  --profile default_household --golongan "R-1/TR 1300 VA" \
  --out examples/report_7d.md

# 3. Dashboard HTML statis (buka di browser; butuh internet untuk Chart.js CDN)
python -m iot_home_energy_monitor dashboard --input examples/sim_7d.csv \
  --report examples/report_7d.json --out examples/dashboard/index.html

# 4. Hitung tagihan / konversi token langsung
python -m iot_home_energy_monitor bill --kwh 250 --golongan "R-1/TR 1300 VA" --ppj 3
python -m iot_home_energy_monitor bill --token 50000 --golongan "R-1/TR 1300 VA" --ppj 3
```

Semua contoh di `examples/` dapat dibuat ulang dengan:

```bash
bash examples/run_examples.sh
```

## Contoh output (asli, dari run beneran)

Simulasi 7 hari, profil `default_household`, seed 42
(10–16 November 2026, 10.080 menit):

```
CSV ditulis: examples/sim_7d.csv (10080 menit)
Profil: default_household | 7 hari | total 65.69 kWh (9.38 kWh/hari)
Total 65.69 kWh dalam 7 hari; estimasi tagihan bulanan Rp418,917.77 (R-1/TR 1300 VA)
```

Konsumsi per alat (7 hari):

| Alat | kWh | Pangsa |
| --- | ---: | ---: |
| ac_1pk | 31,71 | 48,3% |
| kulkas | 10,08 | 15,3% |
| kipas_angin | 6,74 | 10,3% |
| rice_cooker_masak | 5,60 | 8,5% |
| tv | 2,54 | 3,9% |
| lampu | 2,10 | 3,2% |
| rice_cooker_hangat | 1,94 | 3,0% |
| dispenser | 1,72 | 2,6% |
| mesin_cuci | 1,23 | 1,9% |
| pompa_air | 1,19 | 1,8% |
| beban siaga | 0,84 | 1,3% |

Angka kunci lain: daya puncak **1.215 W** (10 Nov 2026, 21:02 — AC +
TV + lampu + kulkas + kipas bersamaan); jam tersibuk 0,97 kWh
(14 Nov, 21:01); faktor beban 0,322; **11 lonjakan** di atas 1.040 W
yang bertahan ≥ 5 menit; 0 hari anomali; konsumsi harian stabil
9,13–9,69 kWh.

Estimasi tagihan bulanan (rata-rata harian × 30 hari = 281,52 kWh,
golongan R-1/TR 1300 VA, tarif Rp1.444,70/kWh, PPJ 3%):

| Komponen | Rp |
| --- | ---: |
| Biaya energi (281,52 kWh) | 406.716,28 |
| PPJ (3%) | 12.201,49 |
| **Total** | **418.917,77** |

Rekomendasi (dihitung dari data, bukan angka karangan): potensi hemat
gabungan **24,21 kWh/bulan (~Rp36.017/bulan)** — terbesar dari AC
(naikkan suhu 1°C / kurangi 1 jam nyala: ~13,6 kWh/bulan) dan mode
hangat rice cooker. Detail lengkap di
[`examples/report_7d.md`](examples/report_7d.md); dashboard di
[`examples/dashboard/index.html`](examples/dashboard/index.html).

Profil kedua, `small_household` (900 VA RTM, tanpa AC): 7 hari =
24,73 kWh (3,53 kWh/hari); estimasi tagihan **Rp147.597,43/bulan**
(105,99 kWh × Rp1.352,00 + PPJ 3%). Alat terbesar di sana justru
kulkas (32,2%).

Hitung tangan tagihan (dipakai sebagai tes regresi):

```
250 kWh di R-1/TR 1300 VA, PPJ 3%:
  biaya energi = 250 × 1.444,70 = Rp361.175,00
  PPJ          = 3% × 361.175,00 = Rp10.835,25
  total        = Rp372.010,25
Token Rp50.000 di 1.300 VA, PPJ 3%:
  (50.000 − 1.500) / 1.444,70 = 33,57 kWh  (cocok dengan pemberitaan)
```

## Keputusan desain

- **Resolusi 1 menit, RNG ber-seed.** Cukup halus untuk menangkap
  puncak dan lonjakan, cukup murah untuk 30 hari (43.200 baris), dan
  hasilnya dapat direproduksi persis dengan seed yang sama.
- **Profil sebagai data (JSON), bukan kode.** Menambah alat atau
  mengubah jadwal tidak butuh menyentuh Python; dua profil bawaan
  disertakan sebagai contoh.
- **Tarif sebagai data (JSON) terpisah dari kode.** Saat ESDM
  menetapkan tarif triwulan baru, cukup ganti satu file data.
- **Tanpa dependensi runtime.** Semua modul memakai standard library;
  pytest hanya untuk pengujian. Dashboard memakai Chart.js dari CDN
  agar satu file HTML bisa dibuka di mana saja.
- **Lonjakan dihitung bila bertahan ≥ 5 menit.** Kombinasi alat yang
  kebetulan menyala 1 menit di atas ambang adalah hal biasa; yang
  bermakna sebagai risiko MCB trip adalah beban tinggi yang bertahan.
- **Rekomendasi dihitung dari angka simulasi.** Setiap estimasi hemat
  memakai pangsa alat hasil simulasi dan skenario yang eksplisit
  (mis. −10% konsumsi AC), dengan sumber klaim umum dicantumkan di
  `docs/RESEARCH.md`.

## Keterbatasan & pengembangan

- Profil pemakaian adalah **tipikal, bukan pengukuran** — angka daya
  dan jadwal berasal dari acuan umum, bukan meteran satu rumah nyata.
  Untuk data sendiri, ganti `data/profiles/*.json` atau impor CSV
  dari smart meter (format kolom sama dengan output `simulate`).
- RNG menit-per-menit tidak memodelkan arus start motor (bisa 5–7×
  daya jalan); daya puncak di sini adalah daya jalan.
- Tarif bisa berubah tiap triwulan; perbarui
  `data/tariffs/pln_q4_2026.json` bila ada penetapan baru. PPJ 3%
  adalah asumsi — tagihan resmi memakai persentase daerah.
- Pengembangan: impor data smart meter nyata (CSV), tarif
  time-of-use bila PLN menerapkannya, model panel surya atap, dan
  deteksi anomali berbasis profil per jam (bukan harian saja).

## Tes

```bash
python -m pytest -q
# 74 passed
```

Tes memakai nilai hitung tangan: tagihan 250 kWh (Rp372.010,25),
token Rp50.000 → 33,57 kWh, energi kulkas 7 hari (10,08 kWh),
agregasi kWh dari deret sintetis, deteksi lonjakan, round-trip
CSV/SQLite, dan end-to-end CLI lewat subprocess.

## Lisensi

MIT — lihat [LICENSE](LICENSE).
