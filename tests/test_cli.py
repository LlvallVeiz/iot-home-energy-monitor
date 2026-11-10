"""Tes end-to-end CLI lewat subprocess (python -m ...)."""

import json
import os
import subprocess
import sys

import pytest

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
SRC = os.path.join(PROJECT_ROOT, "src")
MODULE = [sys.executable, "-m", "iot_home_energy_monitor"]


def _run(args, cwd, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + os.pathsep + env.get("PYTHONPATH", "")
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        MODULE + args, cwd=cwd, env=env,
        capture_output=True, text=True, timeout=120,
    )


def test_cli_simulate_analyze_dashboard(tmp_path):
    csv_path = str(tmp_path / "sim.csv")
    db_path = str(tmp_path / "sim.sqlite")
    result = _run([
        "simulate", "--profile", "default_household", "--days", "3",
        "--start", "2026-11-10", "--seed", "42",
        "--csv", csv_path, "--sqlite", db_path,
    ], cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert os.path.exists(csv_path)
    assert os.path.exists(db_path)
    assert "3 hari" in result.stdout

    md_path = str(tmp_path / "report.md")
    result = _run([
        "analyze", "--input", csv_path, "--profile", "default_household",
        "--golongan", "R-1/TR 1300 VA", "--out", md_path,
    ], cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert os.path.exists(md_path)
    assert os.path.exists(str(tmp_path / "report.json"))
    with open(md_path, encoding="utf-8") as handle:
        assert "Laporan Analisis Energi" in handle.read()

    html_path = str(tmp_path / "dashboard.html")
    result = _run([
        "dashboard", "--input", db_path,
        "--report", str(tmp_path / "report.json"), "--out", html_path,
    ], cwd=str(tmp_path))
    assert result.returncode == 0, result.stderr
    assert os.path.exists(html_path)
    with open(html_path, encoding="utf-8") as handle:
        content = handle.read()
    assert "chart.js" in content.lower()


def test_cli_bill_kwh():
    result = _run([
        "bill", "--kwh", "250", "--golongan", "R-1/TR 1300 VA", "--ppj", "3",
    ], cwd=PROJECT_ROOT)
    assert result.returncode == 0, result.stderr
    assert "372,010.25" in result.stdout  # hitung tangan: 250 kWh


def test_cli_bill_token():
    result = _run([
        "bill", "--token", "50000", "--golongan", "R-1/TR 1300 VA", "--ppj", "3",
    ], cwd=PROJECT_ROOT)
    assert result.returncode == 0, result.stderr
    assert "33.57" in result.stdout  # contoh diberitakan


def test_cli_bill_requires_kwh_or_token():
    result = _run(["bill", "--golongan", "R-1/TR 1300 VA"], cwd=PROJECT_ROOT)
    assert result.returncode != 0


def test_cli_unknown_golongan_rejected():
    result = _run([
        "bill", "--kwh", "100", "--golongan", "R-9/TR 99999 VA",
    ], cwd=PROJECT_ROOT)
    assert result.returncode != 0


def test_cli_simulate_requires_output():
    result = _run([
        "simulate", "--profile", "default_household", "--days", "1",
    ], cwd=PROJECT_ROOT)
    assert result.returncode != 0
