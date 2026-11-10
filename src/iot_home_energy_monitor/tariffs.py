"""Tarif listrik PLN rumah tangga dan perhitungan tagihan.

Sumber data: ``data/tariffs/pln_q4_2026.json`` — tarif Triwulan IV 2026
(1 Oktober–31 Desember 2026) berdasarkan penetapan Kementerian ESDM
(Peraturan Menteri ESDM Nomor 7 Tahun 2024). Tarif rumah tangga PLN
bersifat **flat per kWh per golongan** — bukan blok bertingkat progresif
(sistem blok I/II/III sudah tidak berlaku untuk rumah tangga). Yang
"bertingkat" adalah golongannya: makin besar daya terpasang, makin
tinggi tarif per kWh.

Rumus tagihan pascabayar (sesuai praktik PLN):

    biaya energi = kWh x tarif per kWh
    PPJ         = biaya energi x persen PPJ daerah
    total       = biaya energi + PPJ + biaya admin (bila ada)

Rumus token prabayar (dari contoh yang diberitakan):

    kWh = (nominal - biaya admin - PPJ) / tarif per kWh,
    dengan PPJ = persen PPJ x nominal.

PPJ (Pajak Penerangan Jalan, kini PBJT tenaga listrik) ditetapkan
pemerintah daerah dan berbeda-beda tiap daerah; 3% dipakai sebagai
default karena dipakai dalam contoh hitung resmi yang diberitakan.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

DEFAULT_PPJ_PCT = 3.0

TARIFF_PERIOD = "Triwulan IV 2026 (1 Oktober–31 Desember 2026)"


@dataclass(frozen=True)
class Tariff:
    """Satu golongan tarif rumah tangga PLN."""

    code: str
    golongan: str
    va: int
    va_label: str
    rate_per_kwh: float
    subsidized: bool
    note: str = ""


@dataclass
class Bill:
    """Hasil perhitungan tagihan listrik satu periode."""

    kwh: float
    golongan: str
    rate_per_kwh: float
    energy_cost: float
    ppj_pct: float
    ppj: float
    admin_fee: float
    total: float

    def to_dict(self) -> dict:
        return {
            "kwh": round(self.kwh, 4),
            "golongan": self.golongan,
            "rate_per_kwh": self.rate_per_kwh,
            "energy_cost": round(self.energy_cost, 2),
            "ppj_pct": self.ppj_pct,
            "ppj": round(self.ppj, 2),
            "admin_fee": round(self.admin_fee, 2),
            "total": round(self.total, 2),
        }


def _default_tariff_path() -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "tariffs",
        "pln_q4_2026.json",
    )


def load_tariffs(path: str | None = None) -> tuple[list[Tariff], dict]:
    """Muat tabel tarif dari JSON; kembalikan (daftar tarif, metadata)."""
    path = path or _default_tariff_path()
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    tariffs = [
        Tariff(
            code=item["code"],
            golongan=item["golongan"],
            va=int(item["va"]),
            va_label=item["va_label"],
            rate_per_kwh=float(item["rate_per_kwh"]),
            subsidized=bool(item["subsidized"]),
            note=item.get("note", ""),
        )
        for item in data["tariffs"]
    ]
    meta = {key: value for key, value in data.items() if key != "tariffs"}
    return tariffs, meta


def list_golongan(path: str | None = None) -> list[str]:
    """Daftar kode golongan yang tersedia (untuk CLI dan validasi)."""
    tariffs, _ = load_tariffs(path)
    return [t.code for t in tariffs]


def rate_for(golongan: str, path: str | None = None) -> Tariff:
    """Cari tarif berdasarkan kode golongan (persis seperti di tabel)."""
    tariffs, _ = load_tariffs(path)
    for tariff in tariffs:
        if tariff.code == golongan:
            return tariff
    raise ValueError(
        f"golongan tidak dikenal: {golongan!r}. "
        f"Pilihan: {', '.join(t.code for t in tariffs)}"
    )


def calculate_bill(
    kwh: float,
    golongan: str,
    ppj_pct: float = DEFAULT_PPJ_PCT,
    admin_fee: float = 0.0,
    path: str | None = None,
) -> Bill:
    """Hitung tagihan pascabayar dari pemakaian kWh dan golongan.

    Contoh hitung tangan (golongan R-1/TR 1300 VA, tarif Rp1.444,70):
    250 kWh -> biaya energi 250 x 1444,70 = Rp361.175,00;
    PPJ 3% -> Rp10.835,25; total Rp372.010,25 (tanpa biaya admin).
    """
    if kwh < 0:
        raise ValueError("kwh tidak boleh negatif")
    if ppj_pct < 0:
        raise ValueError("ppj_pct tidak boleh negatif")
    if admin_fee < 0:
        raise ValueError("admin_fee tidak boleh negatif")
    tariff = rate_for(golongan, path)
    energy_cost = kwh * tariff.rate_per_kwh
    ppj = energy_cost * ppj_pct / 100.0
    return Bill(
        kwh=kwh,
        golongan=tariff.code,
        rate_per_kwh=tariff.rate_per_kwh,
        energy_cost=energy_cost,
        ppj_pct=ppj_pct,
        ppj=ppj,
        admin_fee=admin_fee,
        total=energy_cost + ppj + admin_fee,
    )


def token_kwh(
    nominal_rp: float,
    golongan: str,
    ppj_pct: float = DEFAULT_PPJ_PCT,
    admin_fee: float = 0.0,
    path: str | None = None,
) -> float:
    """Hitung kWh yang didapat dari pembelian token prabayar.

    Contoh hitung tangan (diberitakan lensahukum.co.id, 19 Okt 2026):
    token Rp50.000 di golongan 1.300 VA (Rp1.444,70/kWh), PPJ 3%:
    PPJ = 3% x 50.000 = Rp1.500; (50.000 - 1.500) / 1.444,70
    = 33,57 kWh.
    """
    if nominal_rp <= 0:
        raise ValueError("nominal token harus positif")
    if ppj_pct < 0:
        raise ValueError("ppj_pct tidak boleh negatif")
    if admin_fee < 0:
        raise ValueError("admin_fee tidak boleh negatif")
    tariff = rate_for(golongan, path)
    ppj = nominal_rp * ppj_pct / 100.0
    remaining = nominal_rp - admin_fee - ppj
    if remaining <= 0:
        raise ValueError("nominal habis oleh biaya admin + PPJ")
    return remaining / tariff.rate_per_kwh
