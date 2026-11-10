# Dashboard — iot-home-energy-monitor

Buka `index.html` di browser (klik dua kali). Dashboard ini statis:
satu file HTML, data simulasi 7 hari disematkan sebagai JSON, grafik
digambar Chart.js 4.4.1 dari CDN (butuh internet sekali saat membuka).

Isi dashboard:
- Kartu ringkasan: total kWh, rata-rata harian, daya puncak, faktor
  beban, jumlah lonjakan, estimasi tagihan/bulan.
- Kurva beban rata-rata per jam (puncak malam hari karena AC).
- Donat pangsa konsumsi per alat.
- Grafik batang konsumsi harian (7 hari).
- Tabel rincian per alat + tabel estimasi tagihan bulanan.

File ini dibuat ulang dengan:

```bash
python -m iot_home_energy_monitor dashboard --input examples/sim_7d.csv \
  --report examples/report_7d.json --out examples/dashboard/index.html
```
