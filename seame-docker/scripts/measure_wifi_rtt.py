#!/usr/bin/env python3
"""
Run telemetry/latency_test.py and keep the result in logs/measurements/wifi_rtt/.

    python3 scripts/measure_wifi_rtt.py --note "bench, AP mode, radio on" -n 1000 --interval 0.05

--note is required: the conditions (where, ESP mode, radio, anything unusual). Every
other flag goes to latency_test.py unchanged (--host, --port, -n, --interval,
--timeout, --quickack); see python3 ../telemetry/latency_test.py --help.

The run folder gets meta.json, samples.csv (latency_test.py's per-sample CSV) and
values.json (the summary), and history.csv gets one line. latency_test.py itself is
not changed: the summary is worked out again from its CSV, with the same percentiles.
"""
import argparse
import csv
import datetime
import os
import shutil
import signal
import statistics
import subprocess
import sys

from logbook import ROOT, append_history, new_run, write_json

LATENCY_TEST = os.path.join(os.path.dirname(ROOT), 'telemetry', 'latency_test.py')


def pct(sorted_vals, p):                 # same as latency_test.py
    return sorted_vals[min(len(sorted_vals) - 1, int(len(sorted_vals) * p))]


def summarize(samples_csv):
    """Summary of latency_test.py's CSV; None if it has no samples."""
    with open(samples_csv, newline='') as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    rtts = sorted(float(r['rtt_ms']) for r in rows if r['result'] == 'ok')
    lost = sum(r['result'] == 'lost' for r in rows)
    # --interval is the pause between samples, not the period: this is the real rate.
    stamp = '%Y-%m-%d %H:%M:%S.%f'
    duration = (datetime.datetime.strptime(rows[-1]['time'], stamp)
                - datetime.datetime.strptime(rows[0]['time'], stamp)).total_seconds()
    values = {
        'host': rows[0]['host'],
        'duration_s': round(duration, 1),
        'rate_hz': round((len(rows) - 1) / duration, 1) if duration > 0 else None,
        'sent': len(rows), 'answered': len(rtts), 'lost': lost,
        'lost_pct': round(lost / len(rows) * 100, 1),
        'late': sum(int(r['late_frames']) for r in rows),
        'corrupted': int(rows[-1]['corrupted_total']),
    }
    if rtts:
        values.update({
            'min_ms': rtts[0], 'median_ms': round(statistics.median(rtts), 2),
            'p90_ms': pct(rtts, 0.9), 'p99_ms': pct(rtts, 0.99), 'max_ms': rtts[-1],
            'jitter_ms': round(statistics.pstdev(rtts), 2),
        })
    return values


def main():
    parser = argparse.ArgumentParser(
        description='Wi-Fi round trip to the flight controller, kept in logs/measurements/wifi_rtt/. '
                    'Other flags go to telemetry/latency_test.py.')
    parser.add_argument('--note', required=True,
                        help='conditions: where, ESP mode, radio on/off, anything unusual')
    args, passthrough = parser.parse_known_args()
    if '--csv' in passthrough:
        parser.error('--csv is set by this script (samples.csv in the run folder)')

    run = new_run('measurements', 'wifi_rtt',
                  {'note': args.note, 'latency_test_args': passthrough})
    samples = os.path.join(run, 'samples.csv')

    # Ctrl-C must reach latency_test.py (it stops early and still saves its CSV),
    # not kill this script before the summary is written.
    signal.signal(signal.SIGINT, lambda *_: None)
    code = subprocess.run([sys.executable, LATENCY_TEST, *passthrough, '--csv', samples]).returncode

    values = summarize(samples) if os.path.exists(samples) else None
    if values is None:                   # never connected: keep no empty run
        shutil.rmtree(run)
        print('No samples, nothing recorded.', file=sys.stderr)
        return code or 1
    write_json(os.path.join(run, 'values.json'), values)
    append_history(run, {**values, 'args': ' '.join(passthrough), 'note': args.note})
    print(f'recorded in {os.path.relpath(run, ROOT)}')
    return code


if __name__ == '__main__':
    sys.exit(main())
