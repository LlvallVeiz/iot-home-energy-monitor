"""Penyimpanan deret waktu simulasi: CSV dan SQLite.

Format CSV: kolom ``timestamp`` (ISO 8601), satu kolom per alat
(nama alat apa adanya), dan ``total_w``. Format SQLite: tabel
``readings`` dengan kolom yang sama (timestamp disimpan sebagai TEXT
ISO 8601 agar mudah dibaca alat lain).
"""

from __future__ import annotations

import csv
import os
import sqlite3
from datetime import datetime

from .simulator import Reading

TABLE_NAME = "readings"


def _columns(readings: list[Reading]) -> list[str]:
    """Nama kolom alat, dalam urutan kemunculan pertama."""
    columns: list[str] = []
    for reading in readings:
        for name in reading.watts:
            if name not in columns:
                columns.append(name)
    return columns


def write_csv(readings: list[Reading], path: str) -> None:
    """Tulis deret waktu ke CSV (header + 1 baris per menit)."""
    if not readings:
        raise ValueError("tidak ada data untuk ditulis")
    columns = _columns(readings)
    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp"] + columns + ["total_w"])
        for reading in readings:
            row = reading.to_row(columns)
            writer.writerow(
                [reading.timestamp.isoformat()]
                + [f"{row[c]:.2f}" for c in columns]
                + [f"{row['total_w']:.2f}"]
            )


def read_csv(path: str) -> list[Reading]:
    """Baca deret waktu dari CSV yang ditulis :func:`write_csv`."""
    readings: list[Reading] = []
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "timestamp" not in reader.fieldnames:
            raise ValueError(f"CSV tidak punya kolom timestamp: {path}")
        columns = [c for c in reader.fieldnames if c not in ("timestamp", "total_w")]
        for row in reader:
            readings.append(
                Reading(
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    watts={c: float(row[c]) for c in columns},
                )
            )
    return readings


def write_sqlite(readings: list[Reading], path: str) -> None:
    """Tulis deret waktu ke SQLite (tabel ``readings``).

    File yang sudah ada ditimpa: tabel dibuat ulang dari nol.
    """
    if not readings:
        raise ValueError("tidak ada data untuk ditulis")
    columns = _columns(readings)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    try:
        col_defs = ", ".join(f'"{c}" REAL' for c in columns)
        conn.execute(
            f'CREATE TABLE {TABLE_NAME} '
            f"(timestamp TEXT PRIMARY KEY, {col_defs}, total_w REAL)"
        )
        placeholders = ", ".join("?" for _ in range(len(columns) + 2))
        col_names = ", ".join(f'"{c}"' for c in columns)
        rows = [
            (r.timestamp.isoformat(), *[r.watts.get(c, 0.0) for c in columns], r.total_w)
            for r in readings
        ]
        conn.executemany(
            f"INSERT INTO {TABLE_NAME} (timestamp, {col_names}, total_w) "
            f"VALUES ({placeholders})",
            rows,
        )
        conn.commit()
    finally:
        conn.close()


def read_sqlite(path: str) -> list[Reading]:
    """Baca deret waktu dari SQLite (tabel ``readings``)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"file SQLite tidak ditemukan: {path}")
    conn = sqlite3.connect(path)
    try:
        cursor = conn.execute(f"SELECT * FROM {TABLE_NAME} ORDER BY timestamp")
        columns = [d[0] for d in cursor.description]
        if "timestamp" not in columns:
            raise ValueError("tabel readings tidak punya kolom timestamp")
        appliance_cols = [c for c in columns if c not in ("timestamp", "total_w")]
        readings = []
        for row in cursor.fetchall():
            record = dict(zip(columns, row))
            readings.append(
                Reading(
                    timestamp=datetime.fromisoformat(record["timestamp"]),
                    watts={c: float(record[c]) for c in appliance_cols},
                )
            )
        return readings
    finally:
        conn.close()
