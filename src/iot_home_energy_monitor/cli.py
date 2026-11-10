"""CLI iot-home-energy-monitor.

Sub-perintah:
  simulate   N hari -> CSV dan/atau SQLite
  analyze    CSV/SQLite -> laporan Markdown + JSON (+ rekomendasi)
  bill       hitung tagihan dari kWh + golongan (atau kWh dari token)
  dashboard  CSV/SQLite (+ laporan JSON) -> dashboard HTML statis
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from .analysis import summarize
from .appliances import load_builtin_profile, load_profile
from .dashboard import write_dashboard
from .recommendations import generate_recommendations
from .report import build_report, write_report_files
from .simulator import simulate
from .storage import read_csv, read_sqlite, write_csv, write_sqlite
from .tariffs import (
    TARIFF_PERIOD,
    calculate_bill,
    list_golongan,
    token_kwh,
)

DEFAULT_GOLONGAN = "R-1/TR 1300 VA"
DEFAULT_PPJ_PCT = 3.0


def _load_input(path: str):
    """Baca deret waktu dari CSV atau SQLite berdasarkan ekstensi."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return read_csv(path)
    if ext in (".sqlite", ".sqlite3", ".db"):
        return read_sqlite(path)
    raise ValueError(f"format input tidak didukung: {path} (pakai .csv/.sqlite)")


def _resolve_profile(name_or_path: str):
    """Profil bawaan (nama) atau file JSON (path yang mengandung / atau .json)."""
    if os.path.isfile(name_or_path):
        return load_profile(name_or_path)
    return load_builtin_profile(name_or_path)


def cmd_simulate(args: argparse.Namespace) -> int:
    profile = _resolve_profile(args.profile)
    start = date.fromisoformat(args.start) if args.start else date.today()
    readings = simulate(profile, args.days, start=start, seed=args.seed)
    if args.csv:
        write_csv(readings, args.csv)
        print(f"CSV ditulis: {args.csv} ({len(readings)} menit)")
    if args.sqlite:
        write_sqlite(readings, args.sqlite)
        print(f"SQLite ditulis: {args.sqlite} ({len(readings)} menit)")
    if not args.csv and not args.sqlite:
        print("Tidak ada output: beri --csv dan/atau --sqlite.")
        return 2
    total_kwh = sum(r.total_w for r in readings) / 60000.0
    print(f"Profil: {profile.name} | {args.days} hari | "
          f"total {total_kwh:.2f} kWh ({total_kwh / args.days:.2f} kWh/hari)")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    readings = _load_input(args.input)
    profile_name = args.profile
    contracted_va = args.contracted_va
    threshold_w = args.threshold or 0.8 * contracted_va
    summary = summarize(readings, threshold_w)
    monthly_kwh = summary["avg_daily_kwh"] * 30
    bill = calculate_bill(
        monthly_kwh, args.golongan, ppj_pct=args.ppj, admin_fee=args.admin_fee
    )
    recommendations = generate_recommendations(summary, bill, contracted_va)
    markdown, data = build_report(
        summary, bill, recommendations, profile_name, TARIFF_PERIOD
    )
    if args.out:
        json_path = args.json or os.path.splitext(args.out)[0] + ".json"
        write_report_files(markdown, data, args.out, json_path)
        print(f"Laporan ditulis: {args.out} dan {json_path}")
    else:
        print(markdown)
    print(f"Total {summary['total_kwh']:.2f} kWh dalam {summary['n_days']} hari; "
          f"estimasi tagihan bulanan Rp{bill.total:,.2f} ({bill.golongan})")
    return 0


def cmd_bill(args: argparse.Namespace) -> int:
    if args.token is not None:
        kwh = token_kwh(
            args.token, args.golongan, ppj_pct=args.ppj, admin_fee=args.admin_fee
        )
        print(f"Token Rp{args.token:,.0f} ({args.golongan}, PPJ {args.ppj}%) "
              f"= {kwh:.2f} kWh")
        return 0
    bill = calculate_bill(
        args.kwh, args.golongan, ppj_pct=args.ppj, admin_fee=args.admin_fee
    )
    print(f"Golongan: {bill.golongan} (Rp{bill.rate_per_kwh:,.2f}/kWh)")
    print(f"Biaya energi ({bill.kwh:.2f} kWh): Rp{bill.energy_cost:,.2f}")
    print(f"PPJ ({bill.ppj_pct}%): Rp{bill.ppj:,.2f}")
    if bill.admin_fee:
        print(f"Biaya admin: Rp{bill.admin_fee:,.2f}")
    print(f"Total: Rp{bill.total:,.2f}")
    if args.json:
        print(json.dumps(bill.to_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_dashboard(args: argparse.Namespace) -> int:
    readings = _load_input(args.input)
    if args.report:
        with open(args.report, encoding="utf-8") as handle:
            data = json.load(handle)
        summary = data["summary"]
        bill = calculate_bill(
            data["bill_monthly_estimate"]["kwh"],
            data["bill_monthly_estimate"]["golongan"],
            ppj_pct=data["bill_monthly_estimate"]["ppj_pct"],
            admin_fee=data["bill_monthly_estimate"]["admin_fee"],
        )
        profile_name = data["profile"]
    else:
        threshold_w = 0.8 * args.contracted_va
        summary = summarize(readings, threshold_w)
        bill = calculate_bill(
            summary["avg_daily_kwh"] * 30,
            args.golongan,
            ppj_pct=args.ppj,
            admin_fee=args.admin_fee,
        )
        profile_name = args.profile
    write_dashboard(
        summary, bill, readings, profile_name, TARIFF_PERIOD, args.out
    )
    print(f"Dashboard ditulis: {args.out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="iot-energy",
        description="Simulator beban listrik rumah tangga + tarif PLN + dashboard.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sim = sub.add_parser("simulate", help="Simulasikan N hari ke CSV/SQLite.")
    p_sim.add_argument("--profile", default="default_household",
                       help="nama profil bawaan atau path file JSON")
    p_sim.add_argument("--days", type=int, default=7)
    p_sim.add_argument("--start", default=None,
                       help="tanggal mulai YYYY-MM-DD (default: hari ini)")
    p_sim.add_argument("--seed", type=int, default=42)
    p_sim.add_argument("--csv", default=None)
    p_sim.add_argument("--sqlite", default=None)
    p_sim.set_defaults(func=cmd_simulate)

    p_an = sub.add_parser("analyze", help="Analisis CSV/SQLite jadi laporan.")
    p_an.add_argument("--input", required=True, help="file .csv atau .sqlite")
    p_an.add_argument("--profile", default="default_household")
    p_an.add_argument("--golongan", default=DEFAULT_GOLONGAN,
                      choices=list_golongan())
    p_an.add_argument("--contracted-va", type=int, default=1300)
    p_an.add_argument("--threshold", type=float, default=None,
                      help="ambang lonjakan (W); default 80% daya terpasang")
    p_an.add_argument("--ppj", type=float, default=DEFAULT_PPJ_PCT)
    p_an.add_argument("--admin-fee", type=float, default=0.0)
    p_an.add_argument("--out", default=None, help="file laporan .md")
    p_an.add_argument("--json", default=None, help="file laporan .json")
    p_an.set_defaults(func=cmd_analyze)

    p_bill = sub.add_parser("bill", help="Hitung tagihan / konversi token.")
    p_bill.add_argument("--kwh", type=float, default=None)
    p_bill.add_argument("--token", type=float, default=None,
                        help="nominal token Rp -> kWh")
    p_bill.add_argument("--golongan", default=DEFAULT_GOLONGAN,
                        choices=list_golongan())
    p_bill.add_argument("--ppj", type=float, default=DEFAULT_PPJ_PCT)
    p_bill.add_argument("--admin-fee", type=float, default=0.0)
    p_bill.add_argument("--json", action="store_true")
    p_bill.set_defaults(func=cmd_bill)

    p_dash = sub.add_parser("dashboard", help="Generate dashboard HTML statis.")
    p_dash.add_argument("--input", required=True, help="file .csv atau .sqlite")
    p_dash.add_argument("--report", default=None,
                        help="laporan JSON dari analyze (opsional)")
    p_dash.add_argument("--profile", default="default_household")
    p_dash.add_argument("--golongan", default=DEFAULT_GOLONGAN,
                        choices=list_golongan())
    p_dash.add_argument("--contracted-va", type=int, default=1300)
    p_dash.add_argument("--ppj", type=float, default=DEFAULT_PPJ_PCT)
    p_dash.add_argument("--admin-fee", type=float, default=0.0)
    p_dash.add_argument("--out", required=True, help="file HTML output")
    p_dash.set_defaults(func=cmd_dashboard)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "bill" and args.kwh is None and args.token is None:
        parser.error("bill butuh --kwh atau --token")
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
