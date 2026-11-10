"""Entry point: python -m iot_home_energy_monitor <sub-perintah> ..."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
