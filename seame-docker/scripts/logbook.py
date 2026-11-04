#!/usr/bin/env python3
"""
Run folders and history for seame-docker/logs/: one folder per test run or measurement.

    logs/tests/<date>_<time>_<commit>/              one per run of scripts/run_tests.sh
    logs/tests/history.csv                          one line per run, to see trends
    logs/measurements/<name>/<date>_<time>_<commit>/
    logs/measurements/<name>/history.csv

Every run folder has a meta.json: when, which commit and branch, and the files with
uncommitted changes. Changes under ros2_ws/ (the code) mark the run "-dirty": then the
commit alone doesn't say what ran. Other changes (docs) are only listed.

As a library (scripts that run tests or measurements):
    from logbook import new_run, append_history
As a command, to record a measurement taken by hand:
    python3 scripts/logbook.py measure wifi_rtt mean_ms=12.4 p95_ms=30 drops=0 \\
        --note "bench, radio on"
"""
import argparse
import csv
import datetime
import json
import os
import platform
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # seame-docker/
LOGS = os.path.join(ROOT, 'logs')


def git(*args):
    try:
        return subprocess.run(['git', '-C', ROOT, *args], capture_output=True, text=True,
                              check=True).stdout.rstrip()   # keep leading spaces: status columns
    except (OSError, subprocess.CalledProcessError):
        return ''


CODE = 'seame-docker/ros2_ws/'


def describe_tree():
    """Commit, branch and the uncommitted changes, split into code and the rest."""
    changed = [line[3:] for line in git('status', '--porcelain', '--untracked-files=all')
               .splitlines() if line]
    return {
        'commit': git('rev-parse', 'HEAD'),
        'commit_short': git('rev-parse', '--short', 'HEAD'),
        'commit_subject': git('log', '-1', '--format=%s'),
        'branch': git('rev-parse', '--abbrev-ref', 'HEAD'),
        'uncommitted_code': [f for f in changed if CODE in f],
        'uncommitted_other': [f for f in changed if CODE not in f],
    }


def new_run(kind, name=None, extra=None):
    """Create logs/<kind>[/<name>]/<date>_<time>_<commit>[-dirty]/ with meta.json; return path."""
    now = datetime.datetime.now().astimezone()
    tree = describe_tree()
    tag = (tree['commit_short'] or 'nogit') + ('-dirty' if tree['uncommitted_code'] else '')
    parent = os.path.join(LOGS, kind, name) if name else os.path.join(LOGS, kind)
    path = base = os.path.join(parent, f'{now:%Y-%m-%d_%H%M%S}_{tag}')
    n = 1
    while os.path.exists(path):          # two runs in the same second
        n += 1
        path = f'{base}-{n}'
    os.makedirs(path)
    meta = {'kind': kind, 'name': name, 'date': now.isoformat(timespec='seconds'),
            'host': platform.node(), **tree, **(extra or {})}
    write_json(os.path.join(path, 'meta.json'), meta)
    return path


def write_json(path, data):
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
        f.write('\n')


def read_json(path):
    with open(path) as f:
        return json.load(f)


def history_path(run_dir):
    return os.path.join(os.path.dirname(run_dir), 'history.csv')


def append_history(run_dir, values):
    """Add a line to history.csv next to the run folder: run, date, commit, then values."""
    meta = read_json(os.path.join(run_dir, 'meta.json'))
    row = {'run': os.path.basename(run_dir), 'date': meta['date'],
           'commit': meta['commit_short'], 'dirty': bool(meta.get('uncommitted_code')),
           **values}
    path = history_path(run_dir)
    rows = read_history(path)
    fields = list(dict.fromkeys([k for r in rows for k in r] + list(row)))   # keeps old columns
    rows.append(row)
    with open(path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def read_history(path):
    if not os.path.exists(path):
        return []
    with open(path, newline='') as f:
        return list(csv.DictReader(f))


def main():
    parser = argparse.ArgumentParser(description='Record a measurement in logs/measurements/.')
    sub = parser.add_subparsers(dest='cmd', required=True)
    m = sub.add_parser('measure', help='record values measured by hand or by another tool')
    m.add_argument('name', help='what was measured, e.g. wifi_rtt (one folder per name)')
    m.add_argument('values', nargs='+', help='key=value, e.g. mean_ms=12.4')
    m.add_argument('--note', default='', help='conditions: where, setup, anything unusual')
    args = parser.parse_args()

    values = {}
    for item in args.values:
        key, sep, value = item.partition('=')
        if not sep:
            parser.error(f'expected key=value, got {item!r}')
        values[key] = value
    run = new_run('measurements', args.name, {'note': args.note})
    write_json(os.path.join(run, 'values.json'), values)
    append_history(run, {**values, 'note': args.note})
    print(os.path.relpath(run, ROOT))


if __name__ == '__main__':
    sys.exit(main())
