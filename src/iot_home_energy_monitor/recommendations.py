"""Rekomendasi penghematan berbasis data hasil analisis.

Setiap rekomendasi dihitung dari angka simulasi itu sendiri (bukan
angka yang dikarang): estimasi hemat dihitung dari pangsa energi alat
yang bersangkutan dan skenario pengurangan yang eksplisit di teks.
Sumber klaim umum (mis. menaikkan suhu AC 1 derajat) dicantumkan di
``docs/RESEARCH.md``; angka rupiah memakai tarif yang sama dengan
perhitungan tagihan.
"""

from __future__ import annotations

from .tariffs import Bill


def generate_recommendations(
    summary: dict,
    bill: Bill,
    contracted_va: int,
) -> list[dict]:
    """Bangun daftar rekomendasi dari ringkasan analisis + tagihan.

    Args:
        summary: hasil :func:`analysis.summarize`.
        bill: tagihan bulanan hasil :func:`tariffs.calculate_bill`
            (dipakai untuk mengonversi kWh hemat ke rupiah).
        contracted_va: daya terpasang (VA) untuk menilai risiko MCB trip.
    """
    recommendations: list[dict] = []
    shares = summary["share_by_appliance_pct"]
    by_appliance = summary["energy_by_appliance_kwh"]
    total = summary["total_kwh"]
    n_days = max(summary["n_days"], 1)
    monthly_kwh = total / n_days * 30
    rate = bill.rate_per_kwh

    def monthly_saving(kwh_per_day: float) -> dict:
        kwh_month = kwh_per_day * 30
        return {
            "kwh_per_month": round(kwh_month, 2),
            "rp_per_month": round(kwh_month * rate * (1 + bill.ppj_pct / 100), 0),
        }

    # 1. AC dominan -> naikkan suhu / kurangi jam nyala.
    ac_kwh = by_appliance.get("ac_1pk", 0.0)
    if ac_kwh and shares.get("ac_1pk", 0.0) >= 30.0:
        saving = monthly_saving(ac_kwh / n_days * 0.10)
        recommendations.append(
            {
                "id": "ac_setpoint",
                "title": "AC adalah beban terbesar — naikkan suhu 1°C atau kurangi 1 jam nyala",
                "detail": (
                    f"AC memakai {shares['ac_1pk']:.1f}% dari total energi "
                    f"({ac_kwh / n_days:.2f} kWh/hari). Menaikkan suhu dari 22°C ke "
                    "23–24°C atau mematikan AC 1 jam lebih awal diperkirakan "
                    "memangkas ~10% konsumsi AC (aturan umum hemat energi AC; "
                    "lihat docs/RESEARCH.md)."
                ),
                "estimated_saving": saving,
            }
        )

    # 2. Rice cooker mode hangat terus-menerus.
    warm_kwh = by_appliance.get("rice_cooker_hangat", 0.0)
    if warm_kwh and warm_kwh / n_days >= 0.15:
        saving = monthly_saving(warm_kwh / n_days * 0.80)
        recommendations.append(
            {
                "id": "rice_cooker_warm",
                "title": "Cabut rice cooker setelah nasi matang — mode hangat boros diam-diam",
                "detail": (
                    f"Mode hangat memakai {warm_kwh / n_days:.2f} kWh/hari "
                    f"({shares.get('rice_cooker_hangat', 0):.1f}% total) hanya "
                    "untuk menjaga nasi tetap hangat. Mematikan/mencabut setelah "
                    "masak dan menghangatkan ulang saat perlu menghemat ~80% "
                    "dari angka ini."
                ),
                "estimated_saving": saving,
            }
        )

    # 3. Beban siaga (standby).
    base_kwh = summary.get("base_load_kwh", 0.0)
    if base_kwh and base_kwh / n_days >= 0.10:
        saving = monthly_saving(base_kwh / n_days * 0.50)
        recommendations.append(
            {
                "id": "standby",
                "title": "Kurangi beban siaga (standby) — matikan dari stopkontak",
                "detail": (
                    f"Beban siaga {base_kwh / n_days:.2f} kWh/hari "
                    f"({shares.get('__base_load__', 0):.1f}% total) mengalir 24 jam "
                    "dari charger, TV standby, dan router. Memakai stopkontak "
                    "bersaklar untuk perangkat yang tidak perlu menyala terus "
                    "memangkas sekitar setengahnya."
                ),
                "estimated_saving": saving,
            }
        )

    # 4. Lonjakan daya mendekati batas MCB.
    if summary["n_spikes"] > 0:
        peak = summary["peak"]["peak_w"]
        recommendations.append(
            {
                "id": "peak_shaving",
                "title": "Hindari menyalakan alat besar bersamaan (lonjakan daya)",
                "detail": (
                    f"Terdeteksi {summary['n_spikes']} lonjakan di atas "
                    f"{summary['spike_threshold_w']:.0f} W, puncak "
                    f"{peak:.0f} W dari batas {contracted_va} VA. Jangan "
                    "menyalakan AC + rice cooker + pompa air bersamaan; geser "
                    "mesin cuci/pompa ke jam AC belum menyala."
                ),
                "estimated_saving": {"kwh_per_month": 0.0, "rp_per_month": 0},
            }
        )

    # 5. Kulkas: pangsa besar dan menyala 24 jam.
    fridge_kwh = by_appliance.get("kulkas", 0.0)
    if fridge_kwh and shares.get("kulkas", 0.0) >= 12.0:
        saving = monthly_saving(fridge_kwh / n_days * 0.05)
        recommendations.append(
            {
                "id": "fridge",
                "title": "Jaga kulkas tetap efisien — suhu 3–4°C dan karet pintu rapat",
                "detail": (
                    f"Kulkas memakai {shares['kulkas']:.1f}% total energi "
                    f"({fridge_kwh / n_days:.2f} kWh/hari) dan menyala 24 jam. "
                    "Karet pintu yang longgar atau suhu terlalu dingin menaikkan "
                    "duty cycle kompresor; perbaikan kecil diperkirakan menghemat "
                    "~5% konsumsi kulkas."
                ),
                "estimated_saving": saving,
            }
        )

    # 6. Anomali harian.
    if summary["anomalies"]:
        worst = max(summary["anomalies"], key=lambda a: abs(a["z_score"]))
        recommendations.append(
            {
                "id": "anomaly",
                "title": "Periksa hari dengan konsumsi menyimpang",
                "detail": (
                    f"Tanggal {worst['date']} memakai {worst['kwh']:.2f} kWh "
                    f"(z-score {worst['z_score']:.2f}) — jauh di atas rata-rata "
                    f"{summary['avg_daily_kwh']:.2f} kWh/hari. Cek apakah ada "
                    "alat yang tertinggal menyala atau tamu/pemakaian luar biasa "
                    "hari itu."
                ),
                "estimated_saving": {"kwh_per_month": 0.0, "rp_per_month": 0},
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "id": "ok",
                "title": "Profil beban sudah cukup efisien",
                "detail": (
                    "Tidak ada alat yang mendominasi secara ekstrem, tidak ada "
                    "lonjakan di atas ambang, dan tidak ada hari yang menyimpang. "
                    "Pantau terus lewat dashboard tiap bulan."
                ),
                "estimated_saving": {"kwh_per_month": 0.0, "rp_per_month": 0},
            }
        )

    total_saving_kwh = round(
        sum(r["estimated_saving"]["kwh_per_month"] for r in recommendations), 2
    )
    total_saving_rp = round(
        sum(r["estimated_saving"]["rp_per_month"] for r in recommendations), 0
    )
    return {
        "items": recommendations,
        "total_estimated_saving_kwh_per_month": total_saving_kwh,
        "total_estimated_saving_rp_per_month": total_saving_rp,
        "monthly_kwh_estimate": round(monthly_kwh, 2),
    }
