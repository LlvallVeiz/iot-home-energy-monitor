"""Tes simulator + model peralatan.

Nilai ekspektasi:
- Kulkas 150 W, duty 0,40, 24 jam: energi harian ekspektasi
  150 x 0,40 x 24 / 1000 = 1,44 kWh (band toleransi lebar karena
  keacakan binomial: simpangan baku ~0,05 kWh).
- AC 800 W, duty 0,70, jendela 21:00-05:00 (8 jam): ekspektasi
  800 x 0,70 x 8 / 1000 = 4,48 kWh/hari.
- 1 menit pada P watt = P / 60000 kWh.
"""

from datetime import date

import pytest

from iot_home_energy_monitor.appliances import (
    Appliance,
    HouseholdProfile,
    Window,
    load_builtin_profile,
    parse_hhmm,
)
from iot_home_energy_monitor.simulator import (
    daily_totals,
    per_appliance_kwh,
    simulate,
    total_kwh,
)


def _single_appliance_profile(**kwargs):
    return HouseholdProfile(
        name="test",
        description="",
        contracted_va=1300,
        base_load_w=0.0,
        appliances=[Appliance(name="kulkas", power_w=150, duty=0.4,
                               windows=[Window(0, 1440)], **kwargs)],
    )


def test_parse_hhmm():
    assert parse_hhmm("00:00") == 0
    assert parse_hhmm("05:30") == 330
    assert parse_hhmm("24:00") == 1440
    with pytest.raises(ValueError):
        parse_hhmm("25:00")
    with pytest.raises(ValueError):
        parse_hhmm("12:60")


def test_window_validation():
    with pytest.raises(ValueError):
        Window(600, 600)  # kosong
    with pytest.raises(ValueError):
        Window(900, 600)  # terbalik
    with pytest.raises(ValueError):
        Window(0, 1440, days=[7])  # hari tidak valid


def test_appliance_validation():
    with pytest.raises(ValueError):
        Appliance(name="x", power_w=100, duty=1.5, windows=[Window(0, 60)])
    with pytest.raises(ValueError):
        Appliance(name="x", power_w=100, duty=1.0, windows=[])
    with pytest.raises(ValueError):
        Appliance(name="x", power_w=-10, duty=1.0, windows=[Window(0, 60)])


def test_simulation_length_and_order():
    profile = load_builtin_profile("default_household")
    readings = simulate(profile, 3, start=date(2026, 11, 10), seed=42)
    assert len(readings) == 3 * 1440
    assert readings[0].timestamp.isoformat() == "2026-11-10T00:00:00"
    assert readings[-1].timestamp.isoformat() == "2026-11-12T23:59:00"
    assert all(r.total_w >= 0 for r in readings)


def test_simulation_deterministic_same_seed():
    profile = load_builtin_profile("default_household")
    a = simulate(profile, 2, start=date(2026, 11, 10), seed=7)
    b = simulate(profile, 2, start=date(2026, 11, 10), seed=7)
    assert [r.total_w for r in a] == [r.total_w for r in b]
    assert [r.watts for r in a] == [r.watts for r in b]


def test_simulation_differs_with_seed():
    profile = load_builtin_profile("default_household")
    a = simulate(profile, 1, start=date(2026, 11, 10), seed=1)
    b = simulate(profile, 1, start=date(2026, 11, 10), seed=2)
    assert [r.total_w for r in a] != [r.total_w for r in b]


def test_fridge_daily_energy_near_expectation():
    profile = _single_appliance_profile()
    readings = simulate(profile, 7, start=date(2026, 11, 10), seed=42)
    # Ekspektasi 7 x 1,44 = 10,08 kWh; toleransi +-0,5 kWh (7 sigma).
    assert total_kwh(readings) == pytest.approx(10.08, abs=0.5)


def test_ac_only_at_night():
    profile = load_builtin_profile("default_household")
    readings = simulate(profile, 1, start=date(2026, 11, 10), seed=42)
    # 2026-11-10 adalah Selasa. Cek menit 12:00 (siang): AC harus 0.
    noon = readings[12 * 60]
    assert noon.watts["ac_1pk"] == 0.0
    # AC boleh menyala 22:00 — tidak dijamin menyala tiap menit (duty),
    # tapi total energi AC malam > 0 dalam sehari penuh.
    assert per_appliance_kwh(readings)["ac_1pk"] > 3.0
    assert per_appliance_kwh(readings)["ac_1pk"] < 6.0  # ekspektasi 4,48


def test_washing_machine_only_on_scheduled_days():
    profile = load_builtin_profile("default_household")
    # 2026-11-10 Selasa (weekday 1): mesin cuci tidak dijadwalkan.
    tuesday = simulate(profile, 1, start=date(2026, 11, 10), seed=42)
    assert per_appliance_kwh(tuesday).get("mesin_cuci", 0.0) == 0.0
    # 2026-11-11 Rabu (weekday 2): dijadwalkan, energi > 0.
    wednesday = simulate(profile, 1, start=date(2026, 11, 11), seed=42)
    assert per_appliance_kwh(wednesday)["mesin_cuci"] > 0.0


def test_base_load_always_present():
    profile = load_builtin_profile("default_household")
    readings = simulate(profile, 1, start=date(2026, 11, 10), seed=42)
    assert all(r.watts["__base_load__"] == 5.0 for r in readings)
    # Energi beban siaga 1 hari: 5 W x 24 jam = 0,12 kWh.
    assert per_appliance_kwh(readings)["__base_load__"] == pytest.approx(0.12)


def test_total_kwh_hand_check():
    # 60 menit @ 1000 W + 60 menit @ 0 W = 1,0 kWh.
    from iot_home_energy_monitor.simulator import Reading
    from datetime import datetime, timedelta
    base = datetime(2026, 11, 10)
    readings = [
        Reading(timestamp=base + timedelta(minutes=i),
                watts={"a": 1000.0 if i < 60 else 0.0})
        for i in range(120)
    ]
    assert total_kwh(readings) == pytest.approx(1.0)
    assert per_appliance_kwh(readings)["a"] == pytest.approx(1.0)


def test_daily_totals_split():
    profile = load_builtin_profile("small_household")
    readings = simulate(profile, 2, start=date(2026, 11, 10), seed=3)
    days = daily_totals(readings)
    assert len(days) == 2
    assert days[0][0] == date(2026, 11, 10)
    assert days[1][0] == date(2026, 11, 11)
    assert abs(sum(kwh for _, kwh in days) - total_kwh(readings)) < 1e-6


def test_default_profile_expected_daily_kwh():
    profile = load_builtin_profile("default_household")
    expected = profile.expected_daily_kwh()
    # Kulkas 150 x 0,4 x 1440 / 60000 = 1,44 kWh.
    assert expected["kulkas"] == pytest.approx(1.44)
    # AC 800 x 0,7 x 480 / 60000 = 4,48 kWh.
    assert expected["ac_1pk"] == pytest.approx(4.48)
    # Lampu 60 x 1,0 x 300 / 60000 = 0,30 kWh.
    assert expected["lampu"] == pytest.approx(0.30)
    # Total ekspektasi harian ~9,51 kWh (jumlah semua alat, lihat
    # docs/RESEARCH.md). Mesin cuci dihitung penuh (window-nya), bukan
    # rata-rata mingguan, karena fungsi ini mengabaikan filter hari.
    assert sum(expected.values()) == pytest.approx(9.51, abs=0.05)


def test_simulate_rejects_zero_days():
    profile = load_builtin_profile("default_household")
    with pytest.raises(ValueError):
        simulate(profile, 0, start=date(2026, 11, 10))


def test_builtin_profiles_load():
    for name in ("default_household", "small_household"):
        profile = load_builtin_profile(name)
        assert profile.appliances
        assert profile.contracted_va > 0
