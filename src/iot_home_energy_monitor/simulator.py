"""Simulator deret waktu beban listrik rumah tangga, resolusi 1 menit.

Untuk tiap menit, daya tiap alat ditentukan dari profil
(:mod:`appliances`): 0 di luar jendela pemakaian, dan ``power_w`` dengan
peluang ``duty`` di dalam jendela. Keputusan menyala/mati diambil dari
satu ``random.Random`` ber-seed yang dikonsumsi dalam urutan tetap
(hari -> alat -> menit), sehingga simulasi dengan seed yang sama selalu
menghasilkan deret yang identik bit-per-bit.

Energi: 1 menit pada P watt = P / 60000 kWh.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta

from .appliances import MINUTES_PER_DAY, HouseholdProfile

BASE_LOAD_COLUMN = "__base_load__"


@dataclass
class Reading:
    """Satu baris deret waktu: daya (W) tiap alat pada satu menit."""

    timestamp: datetime
    watts: dict[str, float] = field(default_factory=dict)

    @property
    def total_w(self) -> float:
        """Daya total rumah tangga (W) pada menit ini."""
        return sum(self.watts.values())

    def to_row(self, columns: list[str]) -> dict:
        """Baris datar: timestamp + satu kolom per alat + total_w."""
        row = {"timestamp": self.timestamp}
        for column in columns:
            row[column] = self.watts.get(column, 0.0)
        row["total_w"] = self.total_w
        return row


def simulate(
    profile: HouseholdProfile,
    days: int,
    start: date | datetime | None = None,
    seed: int = 42,
) -> list[Reading]:
    """Simulasikan ``days`` hari beban rumah tangga, resolusi 1 menit.

    Args:
        profile: profil rumah tangga (alat, window, duty, beban siaga).
        days: jumlah hari yang disimulasikan (>= 1).
        start: tanggal mulai (default: hari ini). Jam mulai selalu 00:00.
        seed: seed RNG; seed yang sama -> deret yang identik.

    Returns:
        Daftar ``Reading`` sepanjang ``days * 1440`` menit, berurutan.
    """
    if days < 1:
        raise ValueError("days harus >= 1")
    if start is None:
        start = date.today()
    if isinstance(start, datetime):
        start = start.date()
    start_dt = datetime.combine(start, time(0, 0))

    rng = random.Random(seed)
    readings: list[Reading] = []
    for day_offset in range(days):
        day = start_dt + timedelta(days=day_offset)
        weekday = day.weekday()
        for minute in range(MINUTES_PER_DAY):
            watts: dict[str, float] = {}
            for appliance in profile.appliances:
                roll = rng.random()
                watts[appliance.name] = (
                    appliance.power_w
                    if appliance.is_on(minute, weekday, roll)
                    else 0.0
                )
            if profile.base_load_w:
                watts[BASE_LOAD_COLUMN] = profile.base_load_w
            readings.append(
                Reading(
                    timestamp=day + timedelta(minutes=minute),
                    watts=watts,
                )
            )
    return readings


def appliance_columns(profile: HouseholdProfile) -> list[str]:
    """Nama kolom deret waktu sesuai profil (alat + beban siaga bila ada)."""
    columns = [a.name for a in profile.appliances]
    if profile.base_load_w:
        columns.append(BASE_LOAD_COLUMN)
    return columns


def total_kwh(readings: list[Reading]) -> float:
    """Total energi (kWh) dari deret waktu."""
    return sum(r.total_w for r in readings) / 60000.0


def per_appliance_kwh(readings: list[Reading]) -> dict[str, float]:
    """Energi (kWh) per kolom/alat dari deret waktu."""
    totals: dict[str, float] = {}
    for reading in readings:
        for name, watts in reading.watts.items():
            totals[name] = totals.get(name, 0.0) + watts
    return {name: value / 60000.0 for name, value in totals.items()}


def daily_totals(readings: list[Reading]) -> list[tuple[date, float]]:
    """Total energi (kWh) per tanggal, berurutan."""
    by_day: dict[date, float] = {}
    for reading in readings:
        day = reading.timestamp.date()
        by_day[day] = by_day.get(day, 0.0) + reading.total_w
    return [(day, watts / 60000.0) for day, watts in sorted(by_day.items())]
