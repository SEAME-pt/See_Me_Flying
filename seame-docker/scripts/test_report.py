#!/usr/bin/env python3
"""
Turn one test run's raw results into report.md, results.json and a history.csv line.

    python3 scripts/test_report.py logs/tests/<run>

The run folder holds what scripts/run_tests.sh copied out of the container:
console.log and build/<package>/... result files (pytest.xml, *.xunit.xml,
Testing/*/Test.xml). Compares with the previous run in history.csv and lists
what changed. Exits 1 if the build failed or any test failed or errored.
"""
import glob
import gzip
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

from logbook import append_history, history_path, read_history, read_json, write_json

LINTERS = ('copyright', 'flake8', 'pep257', 'mypy', 'xmllint', 'lint_cmake', 'uncrustify',
           'cppcheck', 'cpplint')


def collect(run):
    """Every test case once, plus the CTest entries (one per C++ test file or linter)."""
    cases, ctest = [], []
    for path in sorted(glob.glob(os.path.join(run, 'build', '*', '**', '*.xml'), recursive=True)):
        rel = os.path.relpath(path, os.path.join(run, 'build'))
        pkg = rel.split(os.sep)[0]
        root = ET.parse(path).getroot()
        if root.tag == 'Site':
            for t in root.iter('Test'):
                if t.get('Status'):
                    ctest.append({'package': pkg, 'name': t.findtext('Name'), 'status': t.get('Status')})
            continue
        pytest = os.path.basename(path) == 'pytest.xml'
        for tc in root.iter('testcase'):
            cls = tc.get('classname', '')
            # pytest: drone_mission.test.test_logic -> test_logic; launch tests and linters:
            # test_test_inav.py.xunit.xml -> test_inav, flake8.xunit.xml -> flake8.
            group = cls.split('.')[-1] if pytest else \
                re.sub(r'^test_(test_)', r'\1', os.path.basename(path).split('.')[0])
            status, message = 'passed', ''
            for tag in ('failure', 'error', 'skipped'):
                e = tc.find(tag)
                if e is not None:
                    status = tag
                    text = (e.get('message') or e.text or '').strip()
                    message = text.replace('![CDATA[', '').replace(']]', '').splitlines()[0][:200] \
                        if text else ''
            cases.append({'package': pkg, 'group': group, 'name': tc.get('name'),
                          'time': float(tc.get('time') or 0), 'status': status, 'message': message,
                          'lint': any(k in group.lower() for k in LINTERS)})
    return cases, ctest


def count(cases):
    return {s: sum(c['status'] == s for c in cases) for s in ('passed', 'skipped', 'failure', 'error')}


def main(run):
    log = open(os.path.join(run, 'console.log')).read()
    meta = read_json(os.path.join(run, 'meta.json'))
    cases, ctest = collect(run)
    n = count(cases)
    exits = dict(re.findall(r'### (build|test|test-result) exit=(\d+)', log))
    secs = dict(re.findall(r'### (build|test) exit=\d+ seconds=(\d+)', log))
    env = re.search(r'### ROS_DISTRO=(\S+)\s+(.*?)\s+python (\S+)', log)
    test_part = log.split('### colcon test\n', 1)[-1]
    durations = dict(re.findall(r'Finished <<< (\S+) \[([\d.]+)s\]', test_part))
    build_ok = exits.get('build') == '0'
    failed = [c for c in cases if c['status'] in ('failure', 'error')]
    ok = build_ok and not failed and bool(cases)

    # The previous run, to say what changed.
    history = read_history(history_path(run))
    prev = history[-1] if history else None
    prev_cases = {}
    if prev and os.path.exists(os.path.join(os.path.dirname(run), prev['run'], 'results.json')):
        prev_cases = {(c['package'], c['group'], c['name']): c['status'] for c in read_json(
            os.path.join(os.path.dirname(run), prev['run'], 'results.json'))['cases']}

    L = []
    w = L.append
    verdict = 'PASSED' if ok else ('BUILD FAILED' if not build_ok else 'FAILED')
    dirty, other = meta.get('uncommitted_code', []), meta.get('uncommitted_other', [])
    w(f'# Test run {os.path.basename(run)}: {verdict}')
    w('')
    w(f'- **When:** {meta["date"]}, on {meta["host"]}')
    w(f'- **Code:** `{meta["commit_short"]}` on `{meta["branch"]}`: {meta["commit_subject"]}')
    if dirty:
        w(f'- **Uncommitted code changes were part of this run** ({len(dirty)} file(s)), so the '
          'commit alone does not say what ran: ' + ', '.join(f'`{f}`' for f in dirty))
    if other:
        w(f'- Other uncommitted files (not code, don\'t affect the tests): '
          + ', '.join(f'`{f}`' for f in other))
    if env:
        w(f'- **Environment:** ROS {env.group(1)}, {env.group(2)}, Python {env.group(3)}, '
          'dev container; clean build, the same commands as CI')
    w(f'- **Build:** exit {exits.get("build", "?")}, {secs.get("build", "?")} s. '
      f'**Tests:** exit {exits.get("test", "?")}, {secs.get("test", "?")} s')
    w('')
    w('## Result')
    w('')
    w('| | Test cases | Passed | Skipped | Failed |')
    w('| --- | --- | --- | --- | --- |')
    for label, group in [('Behaviour tests', [c for c in cases if not c['lint']]),
                         ('Lint and style checks', [c for c in cases if c['lint']]),
                         ('**Total**', cases)]:
        g = count(group)
        w(f'| {label} | {len(group)} | {g["passed"]} | {g["skipped"]} | '
          f'{g["failure"] + g["error"]} |')
    w('')
    w(f'colcon\'s own summary counts {len(cases) + len(ctest)} "tests": the {len(cases)} test '
      f'cases plus {len(ctest)} CTest entries (one per C++ test file or linter), which wrap '
      'cases already counted.')

    if failed:
        w('')
        w('## Failures')
        w('')
        w('| Package | File | Test | Message |')
        w('| --- | --- | --- | --- |')
        for c in failed:
            w(f'| `{c["package"]}` | `{c["group"]}` | `{c["name"]}` | {c["message"]} |')
        w('')
        w('The full output of each failure is in `console.log.gz`.')
    if not build_ok:
        w('')
        w('## Build errors')
        w('')
        w('```text')
        build_part = log.split('### colcon build\n', 1)[-1].split('### build exit', 1)[0]
        for line in build_part.splitlines():
            if re.search(r'error|Failed', line):
                w(line[:200])
        w('```')

    w('')
    w('## Compared with the previous run')
    w('')
    if not prev:
        w('No previous run in `history.csv`.')
    else:
        w(f'Previous: `{prev["run"]}` (`{prev["commit"]}`): {prev.get("cases", "?")} cases, '
          f'{prev.get("failed", "?")} failed. Now: {len(cases)} cases, '
          f'{n["failure"] + n["error"]} failed.')
        now = {(c['package'], c['group'], c['name']): c['status'] for c in cases}
        if prev_cases:
            new = sorted(k for k in now if k not in prev_cases)
            gone = sorted(k for k in prev_cases if k not in now)
            changed = sorted(k for k in now if k in prev_cases and now[k] != prev_cases[k])
            for title, keys, fmt in [
                    ('New tests', new, lambda k: now[k]),
                    ('Tests no longer there', gone, lambda k: f'was {prev_cases[k]}'),
                    ('Status changed', changed, lambda k: f'{prev_cases[k]} → {now[k]}')]:
                if keys:
                    w('')
                    w(f'**{title}:**')
                    for k in keys:
                        w(f'- `{k[0]}` `{k[1]}` `{k[2]}`: {fmt(k)}')
            if not (new or gone or changed):
                w('')
                w('Same tests, same results.')

    w('')
    w('## By package')
    w('')
    w('| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |')
    w('| --- | --- | --- | --- | --- | --- | --- |')
    for pkg in sorted({c['package'] for c in cases}):
        pc = [c for c in cases if c['package'] == pkg]
        g = count(pc)
        w(f'| `{pkg}` | {sum(not c["lint"] for c in pc)} | {sum(c["lint"] for c in pc)} | '
          f'{g["passed"]} | {g["skipped"]} | {g["failure"] + g["error"]} | '
          f'{durations.get(pkg, "?")} s |')

    w('')
    w('## Every test')
    groups = {}
    for c in cases:
        groups.setdefault((c['package'], c['group']), []).append(c)
    for (pkg, group), cs in groups.items():
        w('')
        w(f'### `{pkg}` · `{group}` ({len(cs)})')
        w('')
        w('| Test | Result | Time (s) | Note |')
        w('| --- | --- | --- | --- |')
        for c in cs:
            mark = {'passed': 'pass', 'skipped': 'skipped'}.get(c['status'], f'**{c["status"].upper()}**')
            w(f'| `{c["name"]}` | {mark} | {c["time"]:.3f} | {c["message"] if c["status"] != "passed" else ""} |')

    warnings = sorted({line.strip() for line in log.splitlines()
                       if re.search(r'\bwarning\b', line, re.I) and '[WARN]' not in line
                       and 'warnings summary' not in line})
    w('')
    w('## Warnings in the output')
    w('')
    if warnings:
        w('Lines mentioning a warning (node log lines at WARN level left out: those are the '
          'behaviour under test):')
        w('')
        w('```text')
        for line in warnings[:30]:
            w(line[:200])
        w('```')
    else:
        w('None.')

    w('')
    w('## Console summary lines')
    w('')
    w('Packages are tested in parallel, so these lines interleave.')
    w('')
    w('```text')
    for m in re.finditer(r'^(Finished <<< \S+ \[[\d.]+s\]|=+ .*(?:passed|failed).* =+|'
                         r'\d+% tests passed.*|Summary: .*)$', test_part, re.M):
        w(m.group(1))
    w('```')
    w('')
    w('Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with '
      'any failure message: `results.json`.')

    with open(os.path.join(run, 'report.md'), 'w') as f:
        f.write('\n'.join(L) + '\n')
    write_json(os.path.join(run, 'results.json'), {
        'verdict': verdict, 'build_exit': exits.get('build'), 'test_exit': exits.get('test'),
        'counts': {**n, 'cases': len(cases), 'ctest_entries': len(ctest)}, 'cases': cases})
    with open(os.path.join(run, 'console.log'), 'rb') as src, \
            gzip.open(os.path.join(run, 'console.log.gz'), 'wb') as dst:
        shutil.copyfileobj(src, dst)
    os.remove(os.path.join(run, 'console.log'))
    # Everything in the raw XML is now in results.json (and the console log): keep runs small.
    shutil.rmtree(os.path.join(run, 'build'), ignore_errors=True)
    append_history(run, {
        'verdict': verdict, 'cases': len(cases), 'passed': n['passed'], 'skipped': n['skipped'],
        'failed': n['failure'] + n['error'],
        'behaviour': sum(not c['lint'] for c in cases), 'lint': sum(c['lint'] for c in cases),
        'build_s': secs.get('build', ''), 'test_s': secs.get('test', '')})

    print(f'{verdict}: {len(cases)} test cases, {n["passed"]} passed, {n["skipped"]} skipped, '
          f'{n["failure"] + n["error"]} failed')
    print(f'Report: {os.path.join(run, "report.md")}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(os.path.abspath(sys.argv[1])))
