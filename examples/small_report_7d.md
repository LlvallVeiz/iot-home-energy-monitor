# Laporan Analisis Energi Rumah Tangga — small_household

Periode simulasi: 7 hari (10080 menit, resolusi 1 menit). Dibuat: 2026-11-10.
Tarif acuan: Triwulan IV 2026 (1 Oktober–31 Desember 2026).

## Ringkasan

- Total konsumsi: **24.73 kWh** (3.53 kWh/hari rata-rata)
- Estimasi konsumsi bulanan (30 hari): **105.99 kWh**
- Daya puncak: **961 W** pada 2026-11-10T06:05:00
- Jam tersibuk (60 menit): 0.54 kWh mulai 2026-11-13T05:30:00
- Faktor beban: 0.153
- Lonjakan di atas 720 W: 0 kejadian
- Hari anomali: 0

## Konsumsi per Alat

| Alat | kWh | Pangsa |
| --- | ---: | ---: |
| kulkas | 7.96 | 32.2% |
| rice_cooker_masak | 4.90 | 19.8% |
| kipas_angin | 3.39 | 13.7% |
| tv | 2.01 | 8.2% |
| dispenser | 1.69 | 6.8% |
| rice_cooker_hangat | 1.64 | 6.6% |
| lampu | 1.26 | 5.1% |
| pompa_air | 1.03 | 4.2% |
| __base_load__ | 0.84 | 3.4% |

## Konsumsi Harian

| Tanggal | kWh |
| --- | ---: |
| 2026-11-10 | 3.59 |
| 2026-11-11 | 3.51 |
| 2026-11-12 | 3.52 |
| 2026-11-13 | 3.50 |
| 2026-11-14 | 3.57 |
| 2026-11-15 | 3.50 |
| 2026-11-16 | 3.55 |

## Estimasi Tagihan Bulanan

Golongan: **R-1/TR 900 VA RTM** — tarif Rp1,352.00/kWh (PPJ 3.0%).

| Komponen | Rp |
| --- | ---: |
| Biaya energi (105.99 kWh) | 143,298.48 |
| PPJ (3.0%) | 4,298.95 |
| **Total** | **147,597.43** |

Catatan: estimasi bulanan dari rata-rata harian simulasi x 30 hari. PPJ berbeda tiap daerah — ganti persentasenya bila perlu.

## Rekomendasi Penghematan

Potensi hemat gabungan: **9.14 kWh/bulan (~Rp12,722/bulan)** — estimasi dari skenario di tiap butir, bukan janji.

### Cabut rice cooker setelah nasi matang — mode hangat boros diam-diam

Mode hangat memakai 0.23 kWh/hari (6.6% total) hanya untuk menjaga nasi tetap hangat. Mematikan/mencabut setelah masak dan menghangatkan ulang saat perlu menghemat ~80% dari angka ini.

Perkiraan hemat: 5.63 kWh/bulan (~Rp7,840/bulan).

### Kurangi beban siaga (standby) — matikan dari stopkontak

Beban siaga 0.12 kWh/hari (3.4% total) mengalir 24 jam dari charger, TV standby, dan router. Memakai stopkontak bersaklar untuk perangkat yang tidak perlu menyala terus memangkas sekitar setengahnya.

Perkiraan hemat: 1.80 kWh/bulan (~Rp2,507/bulan).

### Jaga kulkas tetap efisien — suhu 3–4°C dan karet pintu rapat

Kulkas memakai 32.2% total energi (1.14 kWh/hari) dan menyala 24 jam. Karet pintu yang longgar atau suhu terlalu dingin menaikkan duty cycle kompresor; perbaikan kecil diperkirakan menghemat ~5% konsumsi kulkas.

Perkiraan hemat: 1.71 kWh/bulan (~Rp2,375/bulan).

