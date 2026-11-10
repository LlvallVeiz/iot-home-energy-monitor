#!/usr/bin/env bash
# Membuat ulang semua contoh di examples/ dari nol.
# Jalankan dari root repo:  bash examples/run_examples.sh
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH=src

python3 -m iot_home_energy_monitor simulate --profile default_household \
  --days 7 --start 2026-11-10 --seed 42 \
  --csv examples/sim_7d.csv --sqlite examples/sim_7d.sqlite

python3 -m iot_home_energy_monitor analyze --input examples/sim_7d.csv \
  --profile default_household --golongan "R-1/TR 1300 VA" \
  --out examples/report_7d.md

python3 -m iot_home_energy_monitor dashboard --input examples/sim_7d.csv \
  --report examples/report_7d.json --out examples/dashboard/index.html

python3 -m iot_home_energy_monitor simulate --profile small_household \
  --days 7 --start 2026-11-10 --seed 42 \
  --csv examples/small_7d.csv

python3 -m iot_home_energy_monitor analyze --input examples/small_7d.csv \
  --profile small_household --golongan "R-1/TR 900 VA RTM" \
  --contracted-va 900 --out examples/small_report_7d.md

echo "Semua contoh dibuat ulang."
