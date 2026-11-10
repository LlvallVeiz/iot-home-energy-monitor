"""Tes tarif PLN + perhitungan tagihan.

Nilai ekspektasi dihitung dengan tangan dari tarif Triwulan IV 2026
(1 Okt–31 Des 2026, Permen ESDM No. 7/2024):

- R-1/TR 1300 VA: Rp1.444,70/kWh
- R-1/TR 900 VA RTM: Rp1.352,00/kWh
- R-2/TR 3500-5500 VA: Rp1.699,53/kWh
- R-1/TR 900 VA subsidi: Rp605,00/kWh
- R-1/TR 450 VA subsidi: Rp415,00/kWh

Hitung tangan tagihan 250 kWh di 1300 VA, PPJ 3%:
    biaya energi = 250 x 1.444,70 = 361.175,00
    PPJ          = 3% x 361.175,00 = 10.835,25
    total        = 372.010,25

Hitung tangan token (contoh diberitakan lensahukum.co.id, 19 Okt 2026):
    token Rp50.000, 1300 VA, PPJ 3%:
    PPJ = 3% x 50.000 = 1.500
    kWh = (50.000 - 1.500) / 1.444,70 = 33,57 kWh
"""

import pytest

from iot_home_energy_monitor.tariffs import (
    calculate_bill,
    list_golongan,
    rate_for,
    token_kwh,
)


def test_rate_table_matches_q4_2026():
    assert rate_for("R-1/TR 1300 VA").rate_per_kwh == pytest.approx(1444.70)
    assert rate_for("R-1/TR 2200 VA").rate_per_kwh == pytest.approx(1444.70)
    assert rate_for("R-1/TR 900 VA RTM").rate_per_kwh == pytest.approx(1352.0)
    assert rate_for("R-1/TR 900 VA (subsidi)").rate_per_kwh == pytest.approx(605.0)
    assert rate_for("R-1/TR 450 VA").rate_per_kwh == pytest.approx(415.0)
    assert rate_for("R-2/TR 3500-5500 VA").rate_per_kwh == pytest.approx(1699.53)
    assert rate_for("R-3/TR 6600 VA+").rate_per_kwh == pytest.approx(1699.53)


def test_rate_table_subsidy_flags():
    assert rate_for("R-1/TR 450 VA").subsidized is True
    assert rate_for("R-1/TR 900 VA (subsidi)").subsidized is True
    assert rate_for("R-1/TR 1300 VA").subsidized is False
    assert rate_for("R-1/TR 900 VA RTM").subsidized is False


def test_all_golongan_listed():
    golongan = list_golongan()
    assert len(golongan) == 7
    assert "R-1/TR 1300 VA" in golongan
    assert "R-2/TR 3500-5500 VA" in golongan


def test_bill_hand_calculation_1300va():
    bill = calculate_bill(250, "R-1/TR 1300 VA", ppj_pct=3.0)
    assert bill.energy_cost == pytest.approx(361175.00, abs=0.01)
    assert bill.ppj == pytest.approx(10835.25, abs=0.01)
    assert bill.total == pytest.approx(372010.25, abs=0.01)
    assert bill.rate_per_kwh == pytest.approx(1444.70)


def test_bill_no_ppj_no_admin():
    bill = calculate_bill(100, "R-1/TR 2200 VA", ppj_pct=0.0)
    assert bill.energy_cost == pytest.approx(144470.0, abs=0.01)
    assert bill.ppj == pytest.approx(0.0)
    assert bill.total == pytest.approx(144470.0, abs=0.01)


def test_bill_subsidized_900va():
    # 100 kWh x Rp605 = Rp60.500; PPJ 3% = Rp1.815; total Rp62.315
    bill = calculate_bill(100, "R-1/TR 900 VA (subsidi)", ppj_pct=3.0)
    assert bill.energy_cost == pytest.approx(60500.0, abs=0.01)
    assert bill.ppj == pytest.approx(1815.0, abs=0.01)
    assert bill.total == pytest.approx(62315.0, abs=0.01)


def test_bill_r2_rate():
    # 200 kWh x Rp1.699,53 = Rp339.906,00; PPJ 10% = Rp33.990,60
    bill = calculate_bill(200, "R-2/TR 3500-5500 VA", ppj_pct=10.0)
    assert bill.energy_cost == pytest.approx(339906.0, abs=0.01)
    assert bill.ppj == pytest.approx(33990.60, abs=0.01)
    assert bill.total == pytest.approx(373896.60, abs=0.01)


def test_bill_admin_fee_added():
    bill = calculate_bill(10, "R-1/TR 1300 VA", ppj_pct=0.0, admin_fee=2500.0)
    assert bill.total == pytest.approx(10 * 1444.70 + 2500.0, abs=0.01)


def test_bill_zero_kwh():
    bill = calculate_bill(0, "R-1/TR 1300 VA")
    assert bill.total == pytest.approx(0.0)


def test_token_hand_calculation_matches_press_example():
    # Contoh diberitakan: Rp50.000 -> 33,57 kWh (1300 VA, PPJ 3%).
    kwh = token_kwh(50000, "R-1/TR 1300 VA", ppj_pct=3.0)
    assert kwh == pytest.approx(33.57, abs=0.01)


def test_token_scales_with_nominal():
    kwh_50k = token_kwh(50000, "R-1/TR 1300 VA", ppj_pct=3.0)
    kwh_100k = token_kwh(100000, "R-1/TR 1300 VA", ppj_pct=3.0)
    assert kwh_100k == pytest.approx(2 * kwh_50k, abs=0.01)


def test_token_admin_fee_reduces_kwh():
    # (50.000 - 2.500 - 1.500) / 1.444,70 = 46.000 / 1.444,70 = 31,84 kWh
    kwh = token_kwh(50000, "R-1/TR 1300 VA", ppj_pct=3.0, admin_fee=2500.0)
    assert kwh == pytest.approx(46000 / 1444.70, abs=0.01)


def test_unknown_golongan_raises():
    with pytest.raises(ValueError, match="golongan tidak dikenal"):
        rate_for("R-9/TR 99999 VA")
    with pytest.raises(ValueError, match="golongan tidak dikenal"):
        calculate_bill(10, "R-9/TR 99999 VA")


def test_negative_inputs_raise():
    with pytest.raises(ValueError):
        calculate_bill(-5, "R-1/TR 1300 VA")
    with pytest.raises(ValueError):
        calculate_bill(10, "R-1/TR 1300 VA", ppj_pct=-1)
    with pytest.raises(ValueError):
        token_kwh(0, "R-1/TR 1300 VA")
    with pytest.raises(ValueError):
        token_kwh(1000, "R-1/TR 1300 VA", admin_fee=99999)


def test_bill_to_dict_rounding():
    bill = calculate_bill(250, "R-1/TR 1300 VA", ppj_pct=3.0)
    data = bill.to_dict()
    assert data["total"] == pytest.approx(372010.25, abs=0.01)
    assert data["golongan"] == "R-1/TR 1300 VA"
    assert data["kwh"] == 250
