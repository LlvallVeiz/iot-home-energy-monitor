"""Tes penyimpanan CSV dan SQLite (round-trip)."""

import os
from datetime import date

import pytest

from iot_home_energy_monitor.appliances import load_builtin_profile
from iot_home_energy_monitor.simulator import simulate
from iot_home_energy_monitor.storage import (
    read_csv,
    read_sqlite,
    write_csv,
    write_sqlite,
)


@pytest.fixture
def readings():
    profile = load_builtin_profile("default_household")
    return simulate(profile, 2, start=date(2026, 11, 10), seed=42)


def test_csv_round_trip(tmp_path, readings):
    path = str(tmp_path / "sim.csv")
    write_csv(readings, path)
    loaded = read_csv(path)
    assert len(loaded) == len(readings) == 2880
    assert loaded[0].timestamp == readings[0].timestamp
    assert loaded[0].watts.keys() == readings[0].watts.keys()
    for original, back in zip(readings[::500], loaded[::500]):
        assert back.total_w == pytest.approx(original.total_w, abs=0.01)


def test_csv_has_expected_header(tmp_path, readings):
    path = str(tmp_path / "sim.csv")
    write_csv(readings, path)
    with open(path, encoding="utf-8") as handle:
        header = handle.readline().strip().split(",")
    assert header[0] == "timestamp"
    assert "kulkas" in header
    assert "ac_1pk" in header
    assert header[-1] == "total_w"


def test_sqlite_round_trip(tmp_path, readings):
    path = str(tmp_path / "sim.sqlite")
    write_sqlite(readings, path)
    loaded = read_sqlite(path)
    assert len(loaded) == len(readings) == 2880
    assert loaded[0].timestamp == readings[0].timestamp
    for original, back in zip(readings[::500], loaded[::500]):
        assert back.total_w == pytest.approx(original.total_w, abs=0.01)


def test_sqlite_row_count_matches(tmp_path, readings):
    import sqlite3

    path = str(tmp_path / "sim.sqlite")
    write_sqlite(readings, path)
    conn = sqlite3.connect(path)
    count = conn.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
    conn.close()
    assert count == 2880


def test_sqlite_overwrite(tmp_path, readings):
    path = str(tmp_path / "sim.sqlite")
    write_sqlite(readings, path)
    write_sqlite(readings[:1440], path)
    assert len(read_sqlite(path)) == 1440


def test_read_missing_sqlite_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        read_sqlite(str(tmp_path / "tidak-ada.sqlite"))


def test_write_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        write_csv([], str(tmp_path / "kosong.csv"))
    with pytest.raises(ValueError):
        write_sqlite([], str(tmp_path / "kosong.sqlite"))


def test_csv_and_sqlite_agree(tmp_path, readings):
    csv_path = str(tmp_path / "sim.csv")
    db_path = str(tmp_path / "sim.sqlite")
    write_csv(readings, csv_path)
    write_sqlite(readings, db_path)
    from_csv = read_csv(csv_path)
    from_db = read_sqlite(db_path)
    assert len(from_csv) == len(from_db)
    assert [r.total_w for r in from_csv] == pytest.approx(
        [r.total_w for r in from_db], abs=0.01
    )
