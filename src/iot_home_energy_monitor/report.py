"""Generator laporan analisis: Markdown (untuk dibaca manusia) dan JSON
(untuk dipakai alat lain / dashboard).
"""

from __future__ import annotations

import json
from datetime import date

from .tariffs import Bill


def build_report(
    summary: dict,
    bill: Bill,
    recommendations: dict,
    profile_name: str,
    tariff_period: str,
) -> tuple[str, dict]:
    """Bangun (markdown, data JSON) dari hasil analisis + tagihan."""
    data = {
        "generated_on": date.today().isoformat(),
        "profile": profile_name,
        "tariff_period": tariff_period,
        "summary": summary,
        "bill_monthly_estimate": bill.to_dict(),
        "recommendations": recommendations,
    }
    md = _render_markdown(data, summary, bill, recommendations)
    return md, data


def _render_markdown(
    data: dict, summary: dict, bill: Bill, recommendations: dict
) -> str:
    lines: list[str] = []
    add = lines.append

    add(f"# Laporan Analisis Energi Rumah Tangga — {data['profile']}")
    add("")
    add(f"Periode simulasi: {summary['n_days']} hari "
        f"({summary['n_minutes']} menit, resolusi 1 menit). "
        f"Dibuat: {data['generated_on']}.")
    add(f"Tarif acuan: {data['tariff_period']}.")
    add("")
    add("## Ringkasan")
    add("")
    add(f"- Total konsumsi: **{summary['total_kwh']:.2f} kWh** "
        f"({summary['avg_daily_kwh']:.2f} kWh/hari rata-rata)")
    add(f"- Estimasi konsumsi bulanan (30 hari): "
        f"**{recommendations['monthly_kwh_estimate']:.2f} kWh**")
    add(f"- Daya puncak: **{summary['peak']['peak_w']:.0f} W** "
        f"pada {summary['peak']['at']}")
    add(f"- Jam tersibuk (60 menit): {summary['peak_hour']['kwh']:.2f} kWh "
        f"mulai {summary['peak_hour']['start']}")
    add(f"- Faktor beban: {summary['load_factor']:.3f}")
    add(f"- Lonjakan di atas {summary['spike_threshold_w']:.0f} W: "
        f"{summary['n_spikes']} kejadian")
    add(f"- Hari anomali: {len(summary['anomalies'])}")
    add("")
    add("## Konsumsi per Alat")
    add("")
    add("| Alat | kWh | Pangsa |")
    add("| --- | ---: | ---: |")
    for name, kwh in summary["energy_by_appliance_kwh"].items():
        share = summary["share_by_appliance_pct"][name]
        add(f"| {name} | {kwh:.2f} | {share:.1f}% |")
    add("")
    add("## Konsumsi Harian")
    add("")
    add("| Tanggal | kWh |")
    add("| --- | ---: |")
    for day in summary["daily_kwh"]:
        add(f"| {day['date']} | {day['kwh']:.2f} |")
    add("")
    if summary["spikes"]:
        add("## Lonjakan Daya")
        add("")
        add("| Mulai | Selesai | Puncak (W) | Durasi (menit) |")
        add("| --- | --- | ---: | ---: |")
        for spike in summary["spikes"]:
            add(f"| {spike['start']} | {spike['end']} | "
                f"{spike['peak_w']:.0f} | {spike['duration_min']} |")
        add("")
    if summary["anomalies"]:
        add("## Hari Anomali")
        add("")
        for anomaly in summary["anomalies"]:
            add(f"- {anomaly['date']}: {anomaly['kwh']:.2f} kWh "
                f"(z-score {anomaly['z_score']:.2f})")
        add("")
    add("## Estimasi Tagihan Bulanan")
    add("")
    add(f"Golongan: **{bill.golongan}** — tarif "
        f"Rp{bill.rate_per_kwh:,.2f}/kWh (PPJ {bill.ppj_pct}%).")
    add("")
    add("| Komponen | Rp |")
    add("| --- | ---: |")
    add(f"| Biaya energi ({bill.kwh:.2f} kWh) | {bill.energy_cost:,.2f} |")
    add(f"| PPJ ({bill.ppj_pct}%) | {bill.ppj:,.2f} |")
    if bill.admin_fee:
        add(f"| Biaya admin | {bill.admin_fee:,.2f} |")
    add(f"| **Total** | **{bill.total:,.2f}** |")
    add("")
    add("Catatan: estimasi bulanan dari rata-rata harian simulasi x 30 hari. "
        "PPJ berbeda tiap daerah — ganti persentasenya bila perlu.")
    add("")
    add("## Rekomendasi Penghematan")
    add("")
    add(f"Potensi hemat gabungan: "
        f"**{recommendations['total_estimated_saving_kwh_per_month']:.2f} kWh/bulan "
        f"(~Rp{recommendations['total_estimated_saving_rp_per_month']:,.0f}/bulan)** "
        f"— estimasi dari skenario di tiap butir, bukan janji.")
    add("")
    for item in recommendations["items"]:
        saving = item["estimated_saving"]
        add(f"### {item['title']}")
        add("")
        add(item["detail"])
        add("")
        if saving["kwh_per_month"]:
            add(f"Perkiraan hemat: {saving['kwh_per_month']:.2f} kWh/bulan "
                f"(~Rp{saving['rp_per_month']:,.0f}/bulan).")
            add("")
    return "\n".join(lines) + "\n"


def write_report_files(
    markdown: str, data: dict, md_path: str, json_path: str
) -> None:
    """Tulis laporan Markdown dan JSON ke file."""
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(markdown)
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
