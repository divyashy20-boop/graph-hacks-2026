#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -v
python3 -m p5memory.run_lab --report results/p5_lab_report_latest.json
