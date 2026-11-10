"""Tes laporan Markdown + JSON dan dashboard HTML."""

import json
from datetime import date

import pytest

from iot_home_energy_monitor.analysis import summarize
from iot_home_energy_monitor.appliances import load_builtin_profile
from iot_home_energy_monitor.dashboard import (
    build_dashboard_data,
    render_dashboard,
)
from iot_home_energy_monitor.recommendations import generate_recommendations
from iot_home_energy_monitor.report import build_report
from iot_home_energy_monitor.simulator import simulate
from iot_home_energy_monitor.tariffs import TARIFF_PERIOD, calculate_bill


@pytest.fixture
def analysis_bundle():
    profile = load_builtin_profile("default_household")
    readings = simulate(profile, 7, start=date(2026, 11, 10), seed=42)
    summary = summarize(readings, threshold_w=0.8 * profile.contracted_va)
    bill = calculate_bill(
        summary["avg_daily_kwh"] * 30, "R-1/TR 1300 VA", ppj_pct=3.0
    )
    recs = generate_recommendations(summary, bill, profile.contracted_va)
    return profile, readings, summary, bill, recs


def test_report_markdown_contains_key_numbers(analysis_bundle):
    profile, _, summary, bill, recs = analysis_bundle
    md, _ = build_report(summary, bill, recs, profile.name, TARIFF_PERIOD)
    assert "# Laporan Analisis Energi" in md
    assert f"{summary['total_kwh']:.2f}" in md
    assert "R-1/TR 1300 VA" in md
    assert f"{bill.total:,.2f}" in md
    assert "kulkas" in md
    assert "ac_1pk" in md
    assert "Rekomendasi" in md


def test_report_json_round_trips(analysis_bundle):
    profile, _, summary, bill, recs = analysis_bundle
    _, data = build_report(summary, bill, recs, profile.name, TARIFF_PERIOD)
    assert data["profile"] == "default_household"
    assert data["summary"]["total_kwh"] == pytest.approx(summary["total_kwh"])
    assert data["bill_monthly_estimate"]["total"] == pytest.approx(bill.total)
    assert data["recommendations"]["items"]
    # JSON harus bisa diserialisasi ulang tanpa error.
    json.dumps(data, ensure_ascii=False)


def test_dashboard_data_shape(analysis_bundle):
    _, readings, summary, bill, _ = analysis_bundle
    data = build_dashboard_data(summary, bill, readings)
    assert len(data["hourly_avg_w"]) == 24
    assert len(data["daily_kwh"]) == 7
    assert len(data["appliances"]) == len(summary["energy_by_appliance_kwh"])
    shares = sum(a["share_pct"] for a in data["appliances"])
    assert shares == pytest.approx(100.0, abs=0.1)


def test_dashboard_html_renders(analysis_bundle):
    profile, readings, summary, bill, _ = analysis_bundle
    data = build_dashboard_data(summary, bill, readings)
    content = render_dashboard(data, profile.name, TARIFF_PERIOD)
    assert "<!DOCTYPE html>" in content
    assert "chart.js" in content.lower()
    assert "kulkas" in content
    assert "ac_1pk" in content
    assert "hourlyChart" in content
    assert "donutChart" in content
    assert "dailyChart" in content
    assert f"{bill.total:,.2f}" in content
    # Data JSON tersemat dan bisa di-parse dari halaman.
    start = content.index("const DATA = ") + len("const DATA = ")
    end = content.index(";", start)
    payload = json.loads(content[start:end])
    assert len(payload["hourly_avg_w"]) == 24


def test_dashboard_hourly_profile_peaks_at_night(analysis_bundle):
    _, readings, summary, bill, _ = analysis_bundle
    data = build_dashboard_data(summary, bill, readings)
    hourly = data["hourly_avg_w"]
    # AC menyala malam: rata-rata jam 02:00 harus jauh lebih tinggi
    # daripada jam 12:00 (siang, tanpa AC).
    assert hourly[2] > hourly[12] * 2
