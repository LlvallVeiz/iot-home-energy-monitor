# Laporan Analisis Energi Rumah Tangga — default_household

Periode simulasi: 7 hari (10080 menit, resolusi 1 menit). Dibuat: 2026-11-10.
Tarif acuan: Triwulan IV 2026 (1 Oktober–31 Desember 2026).

## Ringkasan

- Total konsumsi: **65.69 kWh** (9.38 kWh/hari rata-rata)
- Estimasi konsumsi bulanan (30 hari): **281.52 kWh**
- Daya puncak: **1215 W** pada 2026-11-10T21:02:00
- Jam tersibuk (60 menit): 0.97 kWh mulai 2026-11-14T21:01:00
- Faktor beban: 0.322
- Lonjakan di atas 1040 W: 11 kejadian
- Hari anomali: 0

## Konsumsi per Alat

| Alat | kWh | Pangsa |
| --- | ---: | ---: |
| ac_1pk | 31.71 | 48.3% |
| kulkas | 10.08 | 15.3% |
| kipas_angin | 6.74 | 10.3% |
| rice_cooker_masak | 5.60 | 8.5% |
| tv | 2.54 | 3.9% |
| lampu | 2.10 | 3.2% |
| rice_cooker_hangat | 1.94 | 3.0% |
| dispenser | 1.72 | 2.6% |
| mesin_cuci | 1.23 | 1.9% |
| pompa_air | 1.19 | 1.8% |
| __base_load__ | 0.84 | 1.3% |

## Konsumsi Harian

| Tanggal | kWh |
| --- | ---: |
| 2026-11-10 | 9.16 |
| 2026-11-11 | 9.33 |
| 2026-11-12 | 9.13 |
| 2026-11-13 | 9.67 |
| 2026-11-14 | 9.34 |
| 2026-11-15 | 9.37 |
| 2026-11-16 | 9.69 |

## Lonjakan Daya

| Mulai | Selesai | Puncak (W) | Durasi (menit) |
| --- | --- | ---: | ---: |
| 2026-11-10T21:33:00 | 2026-11-10T21:38:00 | 1215 | 6 |
| 2026-11-11T21:29:00 | 2026-11-11T21:34:00 | 1215 | 6 |
| 2026-11-11T21:36:00 | 2026-11-11T21:43:00 | 1215 | 8 |
| 2026-11-12T21:03:00 | 2026-11-12T21:09:00 | 1215 | 7 |
| 2026-11-13T21:31:00 | 2026-11-13T21:35:00 | 1215 | 5 |
| 2026-11-14T21:11:00 | 2026-11-14T21:22:00 | 1215 | 12 |
| 2026-11-14T21:38:00 | 2026-11-14T21:46:00 | 1215 | 9 |
| 2026-11-15T21:26:00 | 2026-11-15T21:30:00 | 1215 | 5 |
| 2026-11-16T21:01:00 | 2026-11-16T21:06:00 | 1215 | 6 |
| 2026-11-16T21:30:00 | 2026-11-16T21:34:00 | 1215 | 5 |
| 2026-11-16T21:52:00 | 2026-11-16T21:58:00 | 1215 | 7 |

## Estimasi Tagihan Bulanan

Golongan: **R-1/TR 1300 VA** — tarif Rp1,444.70/kWh (PPJ 3.0%).

| Komponen | Rp |
| --- | ---: |
| Biaya energi (281.52 kWh) | 406,716.28 |
| PPJ (3.0%) | 12,201.49 |
| **Total** | **418,917.77** |

Catatan: estimasi bulanan dari rata-rata harian simulasi x 30 hari. PPJ berbeda tiap daerah — ganti persentasenya bila perlu.

## Rekomendasi Penghematan

Potensi hemat gabungan: **24.21 kWh/bulan (~Rp36,017/bulan)** — estimasi dari skenario di tiap butir, bukan janji.

### AC adalah beban terbesar — naikkan suhu 1°C atau kurangi 1 jam nyala

AC memakai 48.3% dari total energi (4.53 kWh/hari). Menaikkan suhu dari 22°C ke 23–24°C atau mematikan AC 1 jam lebih awal diperkirakan memangkas ~10% konsumsi AC (aturan umum hemat energi AC; lihat docs/RESEARCH.md).

Perkiraan hemat: 13.59 kWh/bulan (~Rp20,220/bulan).

### Cabut rice cooker setelah nasi matang — mode hangat boros diam-diam

Mode hangat memakai 0.28 kWh/hari (3.0% total) hanya untuk menjaga nasi tetap hangat. Mematikan/mencabut setelah masak dan menghangatkan ulang saat perlu menghemat ~80% dari angka ini.

Perkiraan hemat: 6.66 kWh/bulan (~Rp9,904/bulan).

### Kurangi beban siaga (standby) — matikan dari stopkontak

Beban siaga 0.12 kWh/hari (1.3% total) mengalir 24 jam dari charger, TV standby, dan router. Memakai stopkontak bersaklar untuk perangkat yang tidak perlu menyala terus memangkas sekitar setengahnya.

Perkiraan hemat: 1.80 kWh/bulan (~Rp2,678/bulan).

### Hindari menyalakan alat besar bersamaan (lonjakan daya)

Terdeteksi 11 lonjakan di atas 1040 W, puncak 1215 W dari batas 1300 VA. Jangan menyalakan AC + rice cooker + pompa air bersamaan; geser mesin cuci/pompa ke jam AC belum menyala.

### Jaga kulkas tetap efisien — suhu 3–4°C dan karet pintu rapat

Kulkas memakai 15.3% total energi (1.44 kWh/hari) dan menyala 24 jam. Karet pintu yang longgar atau suhu terlalu dingin menaikkan duty cycle kompresor; perbaikan kecil diperkirakan menghemat ~5% konsumsi kulkas.

Perkiraan hemat: 2.16 kWh/bulan (~Rp3,215/bulan).

