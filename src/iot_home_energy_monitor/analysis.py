"""Analisis deret waktu beban: agregasi energi, beban puncak, lonjakan,
dan anomali harian.

Semua fungsi bersifat murni (menerima daftar :class:`Reading`) sehingga
mudah diuji dengan deret sintetis yang nilai ekspektasinya dihitung
dengan tangan.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from datetime import datetime

from .simulator import BASE_LOAD_COLUMN, Reading, per_appliance_kwh, total_kwh

MINUTES_PER_HOUR = 60


@dataclass
class SpikeEvent:
    """Satu kejadian lonjakan daya (menit-menit berurutan di atas ambang)."""

    start: datetime
    end: datetime
    peak_w: float
    duration_min: int

    def to_dict(self) -> dict:
        return {
            "start": self.start.isoformat(),
            "end": self.end.isoformat(),
            "peak_w": round(self.peak_w, 1),
            "duration_min": self.duration_min,
        }


def energy_by_appliance(readings: list[Reading]) -> dict[str, float]:
    """Energi (kWh) per alat, diurutkan dari yang terbesar."""
    totals = per_appliance_kwh(readings)
    return dict(sorted(totals.items(), key=lambda item: -item[1]))


def daily_energy(readings: list[Reading]) -> list[dict]:
    """Energi (kWh) per hari: ``[{date, kwh}]``, berurutan."""
    by_day: dict[str, float] = {}
    for reading in readings:
        key = reading.timestamp.date().isoformat()
        by_day[key] = by_day.get(key, 0.0) + reading.total_w
    return [
        {"date": day, "kwh": round(watts / 60000.0, 4)}
        for day, watts in sorted(by_day.items())
    ]


def hourly_profile(readings: list[Reading]) -> list[float]:
    """Profil beban rata-rata per jam (W), jam 0..23, dirata-rata per hari.

    Dipakai untuk grafik kurva beban harian di dashboard.
    """
    sums = [0.0] * 24
    counts = [0] * 24
    for reading in readings:
        hour = reading.timestamp.hour
        sums[hour] += reading.total_w
        counts[hour] += 1
    return [
        round(sums[h] / counts[h], 1) if counts[h] else 0.0 for h in range(24)
    ]


def peak_power(readings: list[Reading]) -> dict:
    """Daya puncak sesaat (W) beserta waktunya."""
    peak = max(readings, key=lambda r: r.total_w)
    return {"peak_w": peak.total_w, "at": peak.timestamp.isoformat()}


def peak_hour(readings: list[Reading]) -> dict:
    """Jendela 60 menit dengan energi terbesar (kWh) beserta jam mulainya."""
    if len(readings) < MINUTES_PER_HOUR:
        raise ValueError("butuh minimal 60 menit data untuk peak hour")
    totals = [r.total_w for r in readings]
    best_start, best_sum = 0, -1.0
    window_sum = sum(totals[:MINUTES_PER_HOUR])
    best_sum = window_sum
    for i in range(1, len(totals) - MINUTES_PER_HOUR + 1):
        window_sum += totals[i + MINUTES_PER_HOUR - 1] - totals[i - 1]
        if window_sum > best_sum:
            best_sum, best_start = window_sum, i
    return {
        "start": readings[best_start].timestamp.isoformat(),
        "kwh": round(best_sum / 60000.0, 4),
    }


def load_factor(readings: list[Reading]) -> float:
    """Faktor beban = daya rata-rata / daya puncak (0..1).

    Mendekati 1 berarti beban merata sepanjang waktu; mendekati 0
    berarti beban terkonsentrasi pada puncak-puncak singkat.
    """
    if not readings:
        raise ValueError("tidak ada data")
    mean_w = sum(r.total_w for r in readings) / len(readings)
    peak_w = max(r.total_w for r in readings)
    return round(mean_w / peak_w, 4) if peak_w > 0 else 0.0


def detect_spikes(
    readings: list[Reading], threshold_w: float, min_duration_min: int = 1
) -> list[SpikeEvent]:
    """Deteksi lonjakan: menit-menit berurutan dengan daya > ambang.

    Ambang default yang dipakai CLI adalah 80% dari daya terpasang
    (mis. 1.040 W untuk 1.300 VA) — di atas itu MCB mulai berisiko trip
    bila beban lain ikut menyala. ``min_duration_min`` menyaring
    lonjakan sesaat (1 menit) yang wajar terjadi saat beberapa alat
    kebetulan menyala bersamaan; lonjakan yang bertahan beberapa menit
    berturut-turut lebih bermakna sebagai risiko trip.
    """
    if threshold_w <= 0:
        raise ValueError("threshold_w harus positif")
    if min_duration_min < 1:
        raise ValueError("min_duration_min harus >= 1")
    events: list[SpikeEvent] = []
    current: list[Reading] = []
    for reading in readings:
        if reading.total_w > threshold_w:
            current.append(reading)
        else:
            if current:
                events.append(_close_spike(current))
                current = []
    if current:
        events.append(_close_spike(current))
    return [e for e in events if e.duration_min >= min_duration_min]


def _close_spike(group: list[Reading]) -> SpikeEvent:
    peak = max(group, key=lambda r: r.total_w)
    return SpikeEvent(
        start=group[0].timestamp,
        end=group[-1].timestamp,
        peak_w=peak.total_w,
        duration_min=len(group),
    )


def detect_daily_anomalies(
    daily: list[dict], z_threshold: float = 2.0
) -> list[dict]:
    """Hari-hari dengan konsumsi menyimpang > ``z_threshold`` simpangan baku
    dari rata-rata harian. Butuh minimal 3 hari data; bila simpangan
    baku 0 (semua hari sama) tidak ada anomali.
    """
    if len(daily) < 3:
        return []
    values = [d["kwh"] for d in daily]
    mean = statistics.fmean(values)
    stdev = statistics.pstdev(values)
    if stdev == 0:
        return []
    anomalies = []
    for entry in daily:
        z = (entry["kwh"] - mean) / stdev
        if abs(z) > z_threshold:
            anomalies.append(
                {"date": entry["date"], "kwh": entry["kwh"], "z_score": round(z, 2)}
            )
    return anomalies


def summarize(readings: list[Reading], threshold_w: float) -> dict:
    """Ringkasan analisis lengkap dalam satu dict (siap jadi JSON)."""
    by_appliance = energy_by_appliance(readings)
    total = total_kwh(readings)
    days = daily_energy(readings)
    # Lonjakan harus bertahan >= 5 menit agar dihitung: kombinasi alat
    # yang kebetulan menyala 1 menit di atas ambang adalah hal biasa.
    spikes = detect_spikes(readings, threshold_w, min_duration_min=5)
    peak = peak_power(readings)
    n_days = len(days)
    return {
        "n_days": n_days,
        "n_minutes": len(readings),
        "total_kwh": round(total, 4),
        "avg_daily_kwh": round(total / n_days, 4) if n_days else 0.0,
        "energy_by_appliance_kwh": {
            name: round(value, 4) for name, value in by_appliance.items()
        },
        "share_by_appliance_pct": {
            name: round(value / total * 100, 2) if total else 0.0
            for name, value in by_appliance.items()
        },
        "daily_kwh": days,
        "peak": peak,
        "peak_hour": peak_hour(readings),
        "load_factor": load_factor(readings),
        "spike_threshold_w": threshold_w,
        "n_spikes": len(spikes),
        "spikes": [event.to_dict() for event in spikes],
        "anomalies": detect_daily_anomalies(days),
        "base_load_kwh": round(by_appliance.get(BASE_LOAD_COLUMN, 0.0), 4),
    }
