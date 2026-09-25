"""Reporting only: read stored R3B labels; never import or execute the study.

python -m src.provenance.r3b_reporting [--write]
--write refreshes marked documentation blocks only; result files are read-only.
"""
from collections import Counter, defaultdict
import argparse
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path('results/R3B_braking_bounds')
REPORT = Path('docs/R3B_INTERVAL_BRAKING_RECOVERABILITY.md')
STATUS = Path('docs/PROJECT_STATUS.md')
REFERENCE = 'P0|AUTH_AT_EFFECTIVE'


def read_csv(root, name):
    with (root / OUTPUT / name).open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def index(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key in result:
            raise ValueError(f'duplicate key: {key}')
        result[key] = row
    if not result:
        raise ValueError('empty result table')
    return result


def table(headers, rows):
    def line(values):
        return '| ' + ' | '.join(str(v).replace('|', r'\|') for v in values) + ' |'
    return '\n'.join([line(headers), line(['---'] * len(headers)), *(line(r) for r in rows)])


def derive(root=ROOT):
    """Aggregate existing labels and compare matched rows, without classifying margins."""
    rows = read_csv(root, 'results.csv')
    index(rows, ['scenario_id'])
    keyed = index(rows, ['v0_kmh', 'mu', 'branch', 'ttc_s'])
    scenarios = index(read_csv(root, 'scenario_table.csv'), ['scenario_id'])
    if set(scenarios) != {(r['scenario_id'],) for r in rows}:
        raise ValueError('scenario_table.csv coverage differs from results.csv')
    counts = dict(sorted(Counter(r['classification'] for r in rows).items()))
    summary = json.loads((root / OUTPUT / 'summary.json').read_text())
    if summary['n_scenarios'] != len(rows) or summary['classification_counts'] != counts:
        raise ValueError('summary.json scenario/classification counts differ from results.csv')
    changes = defaultdict(list)
    transitions = []
    for r in rows:
        ref = keyed[(r['v0_kmh'], r['mu'], REFERENCE, r['ttc_s'])]
        if r['classification'] != ref['classification']:
            changes[(r['v0_kmh'], r['mu'], r['branch'])].append(r['ttc_s'])
            transitions.append((r, ref['classification'], r['classification']))
    policy = index(read_csv(root, 'policy_comparison.csv'), ['speed_kmh', 'mu', 'branch'])
    expected = {(r['v0_kmh'], r['mu'], r['branch']) for r in rows}
    if set(policy) != expected:
        raise ValueError('policy_comparison.csv coverage differs from results.csv')
    for key, p in policy.items():
        stated = p['ttc_values_with_changed_classification'].split(';') if p['ttc_values_with_changed_classification'] else []
        if p['reference'] != REFERENCE or sorted(map(float, stated)) != sorted(map(float, changes[key])):
            raise ValueError(f'policy_comparison.csv transitions differ: {key}')
    order = lambda r: (float(r['ttc_s']), float(r['v0_kmh']), float(r['mu']), r['branch'])
    rows.sort(key=order)
    count_text = f"Scenario count: {len(rows)}. " + '; '.join(f'{k}: {v}' for k, v in counts.items()) + '.'
    branches = sorted({r['branch'] for r in rows})
    axes = sorted({(r['ttc_s'], r['v0_kmh'], r['mu']) for r in rows}, key=lambda a: tuple(map(float, a)))
    matrix = table(['TTC (s)', 'Speed (km/h)', 'μ', *branches],
                   [(t, v, m, *(keyed[(v, m, b, t)]['classification'] for b in branches)) for t, v, m in axes])
    alt = [r for r in rows if r['classification'] != r['classification_if_t1_high_4s']]
    alt_table = table(['Scenario ID', 'Stored classification', 'Stored classification with t1 upper bound 4 s'],
                      [(r['scenario_id'], r['classification'], r['classification_if_t1_high_4s']) for r in alt])
    ttc_counts = ', '.join(f'TTC {t} s: {n}' for t, n in sorted(Counter(r['ttc_s'] for r in alt).items(), key=lambda p: float(p[0])))
    policy_table = table(['Scenario ID', 'Reference classification', 'Branch classification'],
                         [(r['scenario_id'], before, after) for r, before, after in sorted(transitions, key=lambda x: order(x[0]))])
    blocks = {'counts': count_text,
              'classifications': count_text + '\n\n' + matrix + '\n\n' + f'Supplementary t1 changes: {len(alt)} ({ttc_counts}).\n\n' + alt_table,
              'policy': f'Classification changes relative to {REFERENCE}: {len(transitions)} scenario/branch comparisons.\n\n' + policy_table}
    bounds = read_csv(root, 't_required_bounds.csv')
    blocks['bounds'] = table(['Speed (km/h)', 'μ', 'Branch', 'Min (s)', 'Mid (s)', 'Max (s)'],
        [(r['speed_kmh'], r['mu'], r['branch'], r['t_required_min_s'], r['t_required_mid_s'], r['t_required_max_s'])
         for r in sorted(bounds, key=lambda r: (float(r['speed_kmh']), float(r['mu']), r['branch']))])
    groups = defaultdict(list)
    for r in read_csv(root, 'sensitivity.csv'):
        groups[(r['parameter'], r['mu'])].append(r)
    def span(group, field):
        values = [float(r[field]) for r in group]
        return f'{min(values):.5f} to {max(values):.5f}'
    blocks['sensitivity'] = table(['Parameter', 'μ', 'Elasticity range', 'OAT swing share range (fraction)'],
        [(p, m, span(g, 'elasticity_at_mid'), span(g, 'share_of_oat_swing')) for (p, m), g in sorted(groups.items())])
    blocks['policy'] += '\n\nStored policy deltas relative to the reference (seconds):\n\n' + table(
        ['Speed (km/h)', 'μ', 'Branch', 'Mid delta', 'Min delta', 'Max delta'],
        [(p['speed_kmh'], p['mu'], p['branch'], p['delta_t_required_mid_s'], p['delta_t_required_min_s'], p['delta_t_required_max_s'])
         for _, p in sorted(policy.items())])
    return blocks


def marked(name, body):
    return f'<!-- R3B:{name}:START -->\n{body}\n<!-- R3B:{name}:END -->'


def replace_block(text, name, body):
    start, end = f'<!-- R3B:{name}:START -->', f'<!-- R3B:{name}:END -->'
    if text.count(start) != 1 or text.count(end) != 1 or text.index(start) > text.index(end):
        raise ValueError(f'missing, duplicate or reversed reporting markers: {name}')
    a, b = text.index(start), text.index(end) + len(end)
    return text[:a] + marked(name, body) + text[b:]


def check(root=ROOT, write=False):
    blocks = derive(root)
    errors = []
    for path, names in ((REPORT, ['bounds', 'classifications', 'sensitivity', 'policy']), (STATUS, ['counts'])):
        original = (root / path).read_text(encoding='utf-8')
        updated = original
        for name in names:
            updated = replace_block(updated, name, blocks[name])
        if updated != original:
            if write:
                (root / path).write_text(updated, encoding='utf-8')
            else:
                errors.append(f'{path}: reporting block differs from stored results (run --write)')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true')
    args = parser.parse_args()
    try:
        errors = check(write=args.write)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(1, f'R3B reporting: {exc}\n')
    if errors:
        parser.exit(1, '\n'.join(errors) + '\n')
    print('R3B reporting consistent with stored results.')


if __name__ == '__main__':
    main()
