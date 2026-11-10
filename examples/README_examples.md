# Contoh — iot-home-energy-monitor

Semua file di sini adalah output asli dari run beneran (bukan angka
karangan). Buat ulang kapan saja dengan `bash run_examples.sh` dari
root repo (profil `default_household` dan `small_household`, 7 hari,
10–16 November 2026, seed 42).

## Profil default (1300 VA, R-1/TR 1300 VA)

- `sim_7d.csv` — deret waktu 10.080 menit (1 menit/baris): daya (W)
  tiap alat + total. Baris pertama:
  `2026-11-10T00:00:00,...,905.00` (AC 800 + kipas 100 + siaga 5).
- `sim_7d.sqlite` — data yang sama di tabel `readings`.
- `report_7d.md` / `report_7d.json` — laporan analisis + tagihan.
  Total **65,69 kWh / 7 hari (9,38 kWh/hari)**; AC 48,3%, kulkas
  15,3%; puncak 1.215 W (10 Nov 21:02); 11 lonjakan ≥ 5 menit;
  estimasi tagihan bulanan **Rp418.917,77** (281,52 kWh ×
  Rp1.444,70 + PPJ 3%).
- `dashboard/index.html` — dashboard statis (buka di browser;
  butuh internet sekali untuk Chart.js CDN).

## Profil kecil (900 VA RTM, tanpa AC)

- `small_7d.csv` — deret waktu 7 hari yang sama.
- `small_report_7d.md` / `small_report_7d.json` — total **24,73 kWh
  / 7 hari (3,53 kWh/hari)**; kulkas 32,2% (terbesar); estimasi
  tagihan bulanan **Rp147.597,43** (105,99 kWh × Rp1.352,00 + PPJ 3%).
