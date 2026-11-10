"""Tes rekomendasi penghematan berbasis data."""

from datetime import date

import pytest

from iot_home_energy_monitor.analysis import summarize
from iot_home_energy_monitor.appliances import load_builtin_profile
from iot_home_energy_monitor.recommendations import generate_recommendations
from iot_home_energy_monitor.simulator import simulate
from iot_home_energy_monitor.tariffs import calculate_bill


def _summary_and_bill(profile_name="default_household", days=7, seed=42):
    profile = load_builtin_profile(profile_name)
    readings = simulate(profile, days, start=date(2026, 11, 10), seed=seed)
    summary = summarize(readings, threshold_w=0.8 * profile.contracted_va)
    bill = calculate_bill(
        summary["avg_daily_kwh"] * 30, "R-1/TR 1300 VA", ppj_pct=3.0
    )
    return summary, bill, profile


def test_default_household_gets_ac_recommendation():
    summary, bill, profile = _summary_and_bill()
    recs = generate_recommendations(summary, bill, profile.contracted_va)
    ids = [item["id"] for item in recs["items"]]
    assert "ac_setpoint" in ids  # AC > 30% pangsa di profil default


def test_default_household_gets_warm_and_standby_tips():
    summary, bill, profile = _summary_and_bill()
    recs = generate_recommendations(summary, bill, profile.contracted_va)
    ids = [item["id"] for item in recs["items"]]
    assert "rice_cooker_warm" in ids
    assert "standby" in ids


def test_savings_are_positive_and_consistent():
    summary, bill, profile = _summary_and_bill()
    recs = generate_recommendations(summary, bill, profile.contracted_va)
    total_kwh = sum(
        item["estimated_saving"]["kwh_per_month"] for item in recs["items"]
    )
    total_rp = sum(
        item["estimated_saving"]["rp_per_month"] for item in recs["items"]
    )
    assert recs["total_estimated_saving_kwh_per_month"] == pytest.approx(
        total_kwh
    )
    assert recs["total_estimated_saving_rp_per_month"] == pytest.approx(total_rp)
    assert total_kwh > 0
    # Hemat tidak boleh melebihi konsumsi bulanan itu sendiri.
    assert total_kwh < recs["monthly_kwh_estimate"]


def test_small_household_has_no_ac_recommendation():
    summary, bill, profile = _summary_and_bill("small_household")
    bill = calculate_bill(
        summary["avg_daily_kwh"] * 30, "R-1/TR 900 VA RTM", ppj_pct=3.0
    )
    recs = generate_recommendations(summary, bill, profile.contracted_va)
    ids = [item["id"] for item in recs["items"]]
    assert "ac_setpoint" not in ids


def test_flat_profile_gets_ok_recommendation():
    from iot_home_energy_monitor.analysis import summarize as _summarize
    from iot_home_energy_monitor.simulator import Reading
    from datetime import datetime, timedelta

    readings = [
        Reading(timestamp=datetime(2026, 11, 10) + timedelta(minutes=i),
                watts={"lampu": 50.0})
        for i in range(1440)
    ]
    summary = _summarize(readings, threshold_w=1000)
    bill = calculate_bill(36.0, "R-1/TR 1300 VA", ppj_pct=3.0)
    recs = generate_recommendations(summary, bill, 1300)
    assert [item["id"] for item in recs["items"]] == ["ok"]


def test_spike_triggers_peak_recommendation():
    from iot_home_energy_monitor.simulator import Reading
    from datetime import datetime, timedelta

    readings = [
        Reading(timestamp=datetime(2026, 11, 10) + timedelta(minutes=i),
                watts={"a": 2000.0 if 100 <= i < 106 else 100.0})
        for i in range(1440)
    ]
    summary = summarize(readings, threshold_w=1500)
    assert summary["n_spikes"] == 1
    bill = calculate_bill(100.0, "R-1/TR 1300 VA", ppj_pct=3.0)
    recs = generate_recommendations(summary, bill, 1300)
    ids = [item["id"] for item in recs["items"]]
    assert "peak_shaving" in ids
