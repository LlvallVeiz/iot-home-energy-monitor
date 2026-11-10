"""Tes analisis beban.

Nilai ekspektasi dihitung dengan tangan dari deret sintetis:
- 60 menit @ 1000 W lalu 60 menit @ 0 W = 1,0 kWh total.
- Deret datar 500 W selama 120 menit = 1,0 kWh, puncak 500 W,
  faktor beban 1,0.
- Lonjakan: 5 menit @ 3000 W di tengah deret 100 W dengan ambang
  2000 W -> 1 kejadian, durasi 5 menit, puncak 3000 W.
"""

from datetime import datetime, timedelta

import pytest

from iot_home_energy_monitor.analysis import (
    daily_energy,
    detect_daily_anomalies,
    detect_spikes,
    energy_by_appliance,
    hourly_profile,
    load_factor,
    peak_hour,
    peak_power,
    summarize,
)
from iot_home_energy_monitor.simulator import Reading


def _series(powers, start=datetime(2026, 11, 10), name="a"):
    return [
        Reading(timestamp=start + timedelta(minutes=i), watts={name: float(p)})
        for i, p in enumerate(powers)
    ]


def test_energy_by_appliance_hand_check():
    readings = _series([1000] * 60 + [0] * 60)
    totals = energy_by_appliance(readings)
    assert totals["a"] == pytest.approx(1.0)


def test_energy_by_appliance_sorted_desc():
    readings = [
        Reading(timestamp=datetime(2026, 11, 10) + timedelta(minutes=i),
                watts={"kecil": 100.0, "besar": 900.0})
        for i in range(60)
    ]
    totals = energy_by_appliance(readings)
    assert list(totals) == ["besar", "kecil"]
    assert totals["besar"] == pytest.approx(0.9)
    assert totals["kecil"] == pytest.approx(0.1)


def test_daily_energy_two_days():
    readings = _series([600] * 2880)  # 2 hari @ 600 W = 14,4 kWh/hari
    days = daily_energy(readings)
    assert len(days) == 2
    assert days[0] == {"date": "2026-11-10", "kwh": pytest.approx(14.4)}
    assert days[1] == {"date": "2026-11-11", "kwh": pytest.approx(14.4)}


def test_peak_power():
    readings = _series([100] * 10 + [2500] + [100] * 10)
    peak = peak_power(readings)
    assert peak["peak_w"] == 2500.0
    assert peak["at"] == "2026-11-10T00:10:00"


def test_peak_hour_hand_check():
    # Jam pertama 100 W (0,1 kWh), jam kedua 1000 W (1,0 kWh).
    readings = _series([100] * 60 + [1000] * 60)
    result = peak_hour(readings)
    assert result["start"] == "2026-11-10T01:00:00"
    assert result["kwh"] == pytest.approx(1.0)


def test_peak_hour_needs_60_minutes():
    with pytest.raises(ValueError):
        peak_hour(_series([100] * 30))


def test_load_factor_flat_is_one():
    readings = _series([500] * 120)
    assert load_factor(readings) == pytest.approx(1.0)


def test_load_factor_spiky_is_low():
    readings = _series([100] * 110 + [2000] * 10)
    # rata-rata = (110*100 + 10*2000)/120 = 258,33; puncak 2000 -> 0,129
    assert load_factor(readings) == pytest.approx(31000 / 120 / 2000, abs=0.001)


def test_detect_spikes_single_event():
    readings = _series([100] * 30 + [3000] * 5 + [100] * 30)
    events = detect_spikes(readings, threshold_w=2000)
    assert len(events) == 1
    assert events[0].duration_min == 5
    assert events[0].peak_w == 3000.0
    assert events[0].start.isoformat() == "2026-11-10T00:30:00"
    assert events[0].end.isoformat() == "2026-11-10T00:34:00"


def test_detect_spikes_none_below_threshold():
    readings = _series([100] * 60)
    assert detect_spikes(readings, threshold_w=2000) == []


def test_detect_spikes_two_events():
    readings = _series([3000] * 3 + [100] * 10 + [3000] * 2)
    events = detect_spikes(readings, threshold_w=2000)
    assert len(events) == 2
    assert [e.duration_min for e in events] == [3, 2]


def test_detect_spikes_spike_at_end_of_series():
    readings = _series([100] * 10 + [3000] * 4)
    events = detect_spikes(readings, threshold_w=2000)
    assert len(events) == 1
    assert events[0].duration_min == 4


def test_detect_spikes_min_duration_filters_blips():
    # 1 menit di atas ambang + 5 menit di atas ambang: hanya yang 5 menit
    # yang lolos bila min_duration_min=5.
    readings = _series([3000] + [100] * 10 + [3000] * 5)
    assert len(detect_spikes(readings, threshold_w=2000)) == 2
    filtered = detect_spikes(readings, threshold_w=2000, min_duration_min=5)
    assert len(filtered) == 1
    assert filtered[0].duration_min == 5


def test_detect_spikes_invalid_threshold():
    with pytest.raises(ValueError):
        detect_spikes(_series([100] * 5), threshold_w=0)


def test_hourly_profile():
    # Jam 0: 60 menit @ 600 W (rata-rata 600); jam 1: 60 menit @ 0 W.
    readings = _series([600] * 60 + [0] * 60)
    profile = hourly_profile(readings)
    assert len(profile) == 24
    assert profile[0] == pytest.approx(600.0)
    assert profile[1] == pytest.approx(0.0)
    assert profile[2] == 0.0


def test_daily_anomalies_flags_outlier():
    daily = [
        {"date": "2026-11-10", "kwh": 9.0},
        {"date": "2026-11-11", "kwh": 9.2},
        {"date": "2026-11-12", "kwh": 9.1},
        {"date": "2026-11-13", "kwh": 9.0},
        {"date": "2026-11-14", "kwh": 25.0},
    ]
    anomalies = detect_daily_anomalies(daily, z_threshold=1.5)
    assert len(anomalies) == 1
    assert anomalies[0]["date"] == "2026-11-14"


def test_daily_anomalies_needs_three_days():
    assert detect_daily_anomalies([{"date": "2026-11-10", "kwh": 9.0}]) == []
    assert detect_daily_anomalies([
        {"date": "2026-11-10", "kwh": 9.0},
        {"date": "2026-11-11", "kwh": 9.0},
    ]) == []


def test_daily_anomalies_flat_series_has_none():
    daily = [{"date": f"2026-11-{10 + i}", "kwh": 9.0} for i in range(5)]
    assert detect_daily_anomalies(daily) == []


def test_summarize_consistency():
    readings = _series([500] * 1440)  # 1 hari datar 500 W = 12 kWh
    summary = summarize(readings, threshold_w=1000)
    assert summary["n_days"] == 1
    assert summary["total_kwh"] == pytest.approx(12.0)
    assert summary["avg_daily_kwh"] == pytest.approx(12.0)
    assert summary["load_factor"] == pytest.approx(1.0)
    assert summary["n_spikes"] == 0
    assert summary["peak"]["peak_w"] == 500.0
    assert summary["energy_by_appliance_kwh"]["a"] == pytest.approx(12.0)
    assert summary["share_by_appliance_pct"]["a"] == pytest.approx(100.0)
