"""Generator dashboard web statis (satu file HTML + Chart.js via CDN).

Dashboard berisi: kartu ringkasan, kurva beban rata-rata per jam,
donat pangsa per alat, grafik batang konsumsi harian, dan tabel
estimasi tagihan. Tidak butuh server — cukup buka file HTML di browser
(butuh internet sekali untuk memuat Chart.js dari CDN).
"""

from __future__ import annotations

import html
import json

from .analysis import hourly_profile
from .simulator import Reading
from .tariffs import Bill

CHARTJS_CDN = (
    "https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"
)


def build_dashboard_data(
    summary: dict, bill: Bill, readings: list[Reading]
) -> dict:
    """Siapkan struktur data JSON yang disematkan ke dashboard."""
    return {
        "hourly_avg_w": hourly_profile(readings),
        "daily_kwh": summary["daily_kwh"],
        "appliances": [
            {
                "name": name,
                "kwh": summary["energy_by_appliance_kwh"][name],
                "share_pct": summary["share_by_appliance_pct"][name],
            }
            for name in summary["energy_by_appliance_kwh"]
        ],
        "summary": {
            "n_days": summary["n_days"],
            "total_kwh": summary["total_kwh"],
            "avg_daily_kwh": summary["avg_daily_kwh"],
            "peak_w": summary["peak"]["peak_w"],
            "peak_at": summary["peak"]["at"],
            "peak_hour_kwh": summary["peak_hour"]["kwh"],
            "load_factor": summary["load_factor"],
            "n_spikes": summary["n_spikes"],
        },
        "bill": bill.to_dict(),
    }


def render_dashboard(
    data: dict,
    profile_name: str,
    tariff_period: str,
) -> str:
    """Render HTML dashboard lengkap dari data JSON."""
    payload = json.dumps(data, ensure_ascii=False)
    title = html.escape(f"Dashboard Energi — {profile_name}")
    bill = data["bill"]
    summary = data["summary"]

    def card(label: str, value: str, sub: str = "") -> str:
        sub_html = f"<div class='sub'>{html.escape(sub)}</div>" if sub else ""
        return (
            f"<div class='card'><div class='label'>{html.escape(label)}</div>"
            f"<div class='value'>{html.escape(value)}</div>{sub_html}</div>"
        )

    cards = "".join(
        [
            card("Total konsumsi", f"{summary['total_kwh']:.2f} kWh",
                 f"{summary['n_days']} hari simulasi"),
            card("Rata-rata harian", f"{summary['avg_daily_kwh']:.2f} kWh/hari"),
            card("Daya puncak", f"{summary['peak_w']:.0f} W",
                 f"pada {summary['peak_at']}"),
            card("Faktor beban", f"{summary['load_factor']:.3f}"),
            card("Lonjakan daya", f"{summary['n_spikes']} kejadian"),
            card("Estimasi tagihan/bulan",
                 f"Rp{bill['total']:,.0f}",
                 f"{bill['golongan']} · {bill['kwh']:.1f} kWh/bulan"),
        ]
    )

    rows = "".join(
        f"<tr><td>{html.escape(a['name'])}</td>"
        f"<td>{a['kwh']:.2f}</td><td>{a['share_pct']:.1f}%</td></tr>"
        for a in data["appliances"]
    )

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<script src="{CHARTJS_CDN}"></script>
<style>
body {{ font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  margin: 0; background: #f4f6f8; color: #1d2a32; }}
header {{ background: #1d2a32; color: #fff; padding: 24px 32px; }}
header h1 {{ margin: 0 0 4px; font-size: 24px; }}
header p {{ margin: 0; color: #b9c6cc; font-size: 14px; }}
main {{ max-width: 1020px; margin: 0 auto; padding: 24px 16px 48px; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px; margin-bottom: 24px; }}
.card {{ background: #fff; border-radius: 10px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); }}
.card .label {{ font-size: 12px; color: #66788a; text-transform: uppercase;
  letter-spacing: .04em; }}
.card .value {{ font-size: 26px; font-weight: 700; margin-top: 4px; }}
.card .sub {{ font-size: 12px; color: #66788a; margin-top: 4px; }}
section {{ background: #fff; border-radius: 10px; padding: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08); margin-bottom: 24px; }}
section h2 {{ margin: 0 0 12px; font-size: 18px; }}
canvas {{ max-height: 320px; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; }}
@media (max-width: 720px) {{ .grid2 {{ grid-template-columns: 1fr; }} }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
th, td {{ text-align: left; padding: 8px 4px; border-bottom: 1px solid #e5eaee; }}
td:nth-child(2), td:nth-child(3), th:nth-child(2), th:nth-child(3) {{ text-align: right; }}
footer {{ font-size: 12px; color: #66788a; text-align: center; }}
</style>
</head>
<body>
<header>
<h1>{title}</h1>
<p>Simulator beban rumah tangga &middot; Tarif acuan: {html.escape(tariff_period)} &middot;
Dibuat oleh iot-home-energy-monitor</p>
</header>
<main>
<div class="cards">{cards}</div>
<section>
<h2>Kurva beban rata-rata per jam (W)</h2>
<canvas id="hourlyChart"></canvas>
</section>
<div class="grid2">
<section>
<h2>Pangsa konsumsi per alat</h2>
<canvas id="donutChart"></canvas>
</section>
<section>
<h2>Konsumsi harian (kWh)</h2>
<canvas id="dailyChart"></canvas>
</section>
</div>
<section>
<h2>Rincian per alat</h2>
<table>
<tr><th>Alat</th><th>kWh</th><th>Pangsa</th></tr>
{rows}
</table>
</section>
<section>
<h2>Estimasi tagihan bulanan ({html.escape(bill['golongan'])})</h2>
<table>
<tr><th>Komponen</th><th>Rp</th></tr>
<tr><td>Biaya energi ({bill['kwh']:.2f} kWh &times; Rp{bill['rate_per_kwh']:,.2f})</td>
    <td>{bill['energy_cost']:,.2f}</td></tr>
<tr><td>PPJ ({bill['ppj_pct']}%)</td><td>{bill['ppj']:,.2f}</td></tr>
<tr><td><strong>Total</strong></td><td><strong>{bill['total']:,.2f}</strong></td></tr>
</table>
<p style="font-size:12px;color:#66788a">Estimasi bulanan = rata-rata harian simulasi &times; 30 hari.
PPJ berbeda tiap daerah. Tarif rumah tangga PLN bersifat flat per kWh per golongan.</p>
</section>
</main>
<footer>iot-home-energy-monitor &middot; data hasil simulasi, bukan pengukuran meteran</footer>
<script>
const DATA = {payload};
const palette = ["#20a145","#1d2a32","#e8a838","#3a7bd5","#c0392b",
  "#8e44ad","#16a085","#d35400","#7f8c8d","#2c3e50","#27ae60"];
new Chart(document.getElementById("hourlyChart"), {{
  type: "line",
  data: {{ labels: DATA.hourly_avg_w.map((_, i) => i + ":00"),
    datasets: [{{ label: "Daya rata-rata (W)", data: DATA.hourly_avg_w,
      borderColor: "#20a145", backgroundColor: "rgba(32,161,69,.12)",
      fill: true, tension: 0.3 }}] }},
  options: {{ responsive: true,
    scales: {{ y: {{ title: {{ display: true, text: "Watt" }} }} }} }}
}});
new Chart(document.getElementById("donutChart"), {{
  type: "doughnut",
  data: {{ labels: DATA.appliances.map(a => a.name),
    datasets: [{{ data: DATA.appliances.map(a => a.kwh),
      backgroundColor: palette }}] }},
  options: {{ responsive: true,
    plugins: {{ legend: {{ position: "bottom" }} }} }}
}});
new Chart(document.getElementById("dailyChart"), {{
  type: "bar",
  data: {{ labels: DATA.daily_kwh.map(d => d.date),
    datasets: [{{ label: "kWh", data: DATA.daily_kwh.map(d => d.kwh),
      backgroundColor: "#1d2a32" }}] }},
  options: {{ responsive: true,
    scales: {{ y: {{ title: {{ display: true, text: "kWh" }} }} }} }}
}});
</script>
</body>
</html>
"""


def write_dashboard(
    summary: dict,
    bill: Bill,
    readings: list[Reading],
    profile_name: str,
    tariff_period: str,
    output_path: str,
) -> str:
    """Bangun data dashboard dan tulis file HTML; kembalikan isi HTML."""
    data = build_dashboard_data(summary, bill, readings)
    content = render_dashboard(data, profile_name, tariff_period)
    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return content
