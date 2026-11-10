"""Model peralatan rumah tangga dan profil pemakaian harian.

Setiap alat dimodelkan dengan:
- ``power_w``: daya saat menyala (W) — angka label/nameplate tipikal.
- ``windows``: jendela waktu (jam:menit) saat alat *boleh* menyala.
- ``duty``: fraksi menit di dalam jendela saat alat benar-benar menyala
  (0..1). Ini memodelkan siklus hidup-mati kompresor/termostat
  (kulkas, AC, dispenser) atau pemakaian sebentar-sebentar (pompa air).

Daya alat di luar jendela selalu 0. Di dalam jendela, tiap menit
diputuskan menyala/mati oleh RNG ber-seed (lihat :mod:`simulator`),
sehingga hasil simulasi dapat direproduksi persis dengan seed yang sama.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field

MINUTES_PER_DAY = 1440


def parse_hhmm(text: str) -> int:
    """Ubah "HH:MM" menjadi menit sejak 00:00 (0..1440)."""
    parts = text.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"format jam tidak valid: {text!r} (pakai HH:MM)")
    hour, minute = int(parts[0]), int(parts[1])
    if not (0 <= hour <= 24 and 0 <= minute < 60):
        raise ValueError(f"jam di luar jangkauan: {text!r}")
    if hour == 24 and minute != 0:
        raise ValueError(f"jam di luar jangkauan: {text!r}")
    return hour * 60 + minute


def format_minute(minute: int) -> str:
    """Ubah menit sejak 00:00 menjadi "HH:MM"."""
    minute = minute % MINUTES_PER_DAY
    return f"{minute // 60:02d}:{minute % 60:02d}"


@dataclass
class Window:
    """Satu jendela waktu harian saat alat boleh menyala.

    ``days`` memakai konvensi ``datetime.weekday()`` (Senin=0 .. Minggu=6);
    ``None`` berarti setiap hari.
    """

    start: int  # menit sejak 00:00, inklusif
    end: int  # menit sejak 00:00, eksklusif; 1440 = 24:00
    days: list[int] | None = None

    def __post_init__(self) -> None:
        if not (0 <= self.start < MINUTES_PER_DAY):
            raise ValueError(f"start window di luar jangkauan: {self.start}")
        if not (0 < self.end <= MINUTES_PER_DAY):
            raise ValueError(f"end window di luar jangkauan: {self.end}")
        if self.end <= self.start:
            raise ValueError(
                f"window kosong/terbalik: {self.start}-{self.end} "
                "(jendela yang melewati tengah malam ditulis sebagai dua window)"
            )
        if self.days is not None:
            for day in self.days:
                if not (0 <= day <= 6):
                    raise ValueError(f"hari tidak valid: {day}")

    def covers(self, minute: int, weekday: int) -> bool:
        """True bila menit (0..1439) dan hari ini masuk window."""
        if self.days is not None and weekday not in self.days:
            return False
        return self.start <= minute < self.end

    @classmethod
    def from_dict(cls, data: dict) -> "Window":
        return cls(
            start=parse_hhmm(data["start"]),
            end=parse_hhmm(data["end"]),
            days=data.get("days"),
        )

    def to_dict(self) -> dict:
        out = {
            "start": format_minute(self.start),
            "end": format_minute(self.end),
        }
        if self.days is not None:
            out["days"] = list(self.days)
        return out


@dataclass
class Appliance:
    """Satu peralatan listrik beserta pola pemakaiannya."""

    name: str
    power_w: float
    duty: float = 1.0
    windows: list[Window] = field(default_factory=list)
    note: str = ""

    def __post_init__(self) -> None:
        if self.power_w < 0:
            raise ValueError(f"daya negatif untuk {self.name!r}")
        if not (0.0 <= self.duty <= 1.0):
            raise ValueError(f"duty di luar 0..1 untuk {self.name!r}: {self.duty}")
        if not self.windows:
            raise ValueError(f"alat {self.name!r} tidak punya window pemakaian")

    def is_on(self, minute: int, weekday: int, roll: float) -> bool:
        """True bila alat menyala pada menit ini.

        ``roll`` adalah bilangan acak seragam [0, 1) dari RNG simulasi;
        alat menyala bila ada window yang mencakup menit ini dan
        ``roll < duty``.
        """
        for window in self.windows:
            if window.covers(minute, weekday):
                return roll < self.duty
        return False

    @classmethod
    def from_dict(cls, data: dict) -> "Appliance":
        return cls(
            name=data["name"],
            power_w=float(data["power_w"]),
            duty=float(data.get("duty", 1.0)),
            windows=[Window.from_dict(w) for w in data["windows"]],
            note=data.get("note", ""),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "power_w": self.power_w,
            "duty": self.duty,
            "windows": [w.to_dict() for w in self.windows],
            "note": self.note,
        }

    def expected_daily_kwh(self) -> float:
        """Energi harian ekspektasi (kWh) bila semua window berlaku tiap hari.

        Nilai ekspektasi = daya x duty x total durasi window / 60000.
        Dipakai untuk memeriksa kewajaran profil tanpa menjalankan simulasi.
        """
        minutes = sum(w.end - w.start for w in self.windows)
        return self.power_w * self.duty * minutes / 60000.0


@dataclass
class HouseholdProfile:
    """Profil satu rumah tangga: daftar alat + beban siaga + daya terpasang."""

    name: str
    description: str
    contracted_va: int
    base_load_w: float = 0.0
    appliances: list[Appliance] = field(default_factory=list)
    base_load_note: str = ""

    def __post_init__(self) -> None:
        if self.contracted_va <= 0:
            raise ValueError("contracted_va harus positif")
        if self.base_load_w < 0:
            raise ValueError("base_load_w negatif")
        names = [a.name for a in self.appliances]
        if len(set(names)) != len(names):
            raise ValueError(f"nama alat ganda di profil: {names}")

    @classmethod
    def from_dict(cls, data: dict) -> "HouseholdProfile":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            contracted_va=int(data["contracted_va"]),
            base_load_w=float(data.get("base_load_w", 0.0)),
            appliances=[Appliance.from_dict(a) for a in data["appliances"]],
            base_load_note=data.get("base_load_note", ""),
        )

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "contracted_va": self.contracted_va,
            "base_load_w": self.base_load_w,
            "base_load_note": self.base_load_note,
            "appliances": [a.to_dict() for a in self.appliances],
        }

    def expected_daily_kwh(self) -> dict[str, float]:
        """Energi harian ekspektasi per alat (kWh), termasuk beban siaga."""
        out = {a.name: a.expected_daily_kwh() for a in self.appliances}
        out["__base_load__"] = self.base_load_w * 24 / 1000.0
        return out


def _default_profiles_dir() -> str:
    return os.path.join(
        os.path.dirname(__file__), "..", "..", "data", "profiles"
    )


def load_profile(path: str) -> HouseholdProfile:
    """Muat profil rumah tangga dari file JSON."""
    with open(path, encoding="utf-8") as handle:
        return HouseholdProfile.from_dict(json.load(handle))


def list_builtin_profiles() -> list[str]:
    """Daftar nama profil bawaan (file JSON di data/profiles/)."""
    folder = _default_profiles_dir()
    if not os.path.isdir(folder):
        return []
    return sorted(
        name[: -len(".json")]
        for name in os.listdir(folder)
        if name.endswith(".json")
    )


def load_builtin_profile(name: str) -> HouseholdProfile:
    """Muat profil bawaan berdasarkan nama (tanpa ekstensi .json)."""
    path = os.path.join(_default_profiles_dir(), f"{name}.json")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"profil bawaan tidak ditemukan: {name!r}")
    return load_profile(path)
