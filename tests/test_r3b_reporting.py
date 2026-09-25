"""Mutation checks on copied output/documents; never run the scientific study."""
import csv
import json
from pathlib import Path
import shutil

import pytest

from src.provenance import r3b_reporting as reporting


@pytest.fixture
def snapshot(tmp_path):
    shutil.copytree(reporting.ROOT / reporting.OUTPUT, tmp_path / reporting.OUTPUT)
    (tmp_path / 'docs').mkdir()
    for path in (reporting.REPORT, reporting.STATUS):
        shutil.copyfile(reporting.ROOT / path, tmp_path / path)
    return tmp_path


def edit(root, path, before, after):
    target = root / path
    text = target.read_text()
    assert before in text
    target.write_text(text.replace(before, after, 1))


def test_committed_reporting_matches():
    assert reporting.check() == []


@pytest.mark.parametrize('mutation', ['omission', 'classification', 'count', 'policy', 't1', 'bounds', 'sensitivity'])
def test_prose_mutations_rejected(snapshot, mutation):
    path = reporting.REPORT
    text = (snapshot / path).read_text()
    if mutation == 'omission':
        # Regression A: remove the complete TTC 3 / 60 km/h / reduced-friction row.
        line = next(s for s in text.splitlines() if s.startswith('| 3.0 | 60 | 0.5 |'))
        assert 'PARAMETER-SENSITIVE' in line
        edit(snapshot, path, line + '\n', '')
    elif mutation == 'classification':
        start = text.index('<!-- R3B:classifications:START -->')
        target = text.index('PARAMETER-SENSITIVE', text.index('| 2.0 |', start))
        (snapshot / path).write_text(text[:target] + text[target:].replace('PARAMETER-SENSITIVE', 'ROBUSTLY SATISFIED', 1))
    elif mutation == 'count':
        edit(snapshot, reporting.STATUS, 'Scenario count: 150.', 'Scenario count: 149.')
    elif mutation in ('policy', 't1'):
        block = 'policy' if mutation == 'policy' else 'classifications'
        part = text.split(f'<!-- R3B:{block}:START -->')[1]
        line = next(s for s in part.splitlines() if s.startswith('| v'))
        edit(snapshot, path, line + '\n', '')
    else:
        part = text.split(f'<!-- R3B:{mutation}:START -->')[1]
        line = part.splitlines()[3]
        edit(snapshot, path, line, line + ' changed')
    assert reporting.check(snapshot)


@pytest.mark.parametrize('field', ['n_scenarios', 'classification_counts'])
def test_json_count_mutations_rejected(snapshot, field):
    path = snapshot / reporting.OUTPUT / 'summary.json'
    summary = json.loads(path.read_text())
    if field == 'n_scenarios':
        summary[field] -= 1
    else:
        summary[field]['PARAMETER-SENSITIVE'] -= 1
    path.write_text(json.dumps(summary))
    with pytest.raises(ValueError, match='counts differ'):
        reporting.check(snapshot)


def test_policy_output_mutation_rejected(snapshot):
    path = snapshot / reporting.OUTPUT / 'policy_comparison.csv'
    rows = reporting.read_csv(snapshot, path.name)
    next(r for r in rows if r['ttc_values_with_changed_classification'])['ttc_values_with_changed_classification'] = ''
    with path.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match='transitions differ'):
        reporting.check(snapshot)


@pytest.mark.parametrize('kind', ['missing', 'duplicate'])
def test_markers_fail_closed(snapshot, kind):
    marker = '<!-- R3B:classifications:START -->'
    edit(snapshot, reporting.REPORT, marker, '' if kind == 'missing' else marker * 2)
    with pytest.raises(ValueError, match='markers'):
        reporting.check(snapshot)


def test_generation_deterministic_and_results_read_only(snapshot):
    before = {p.name: p.read_bytes() for p in (snapshot / reporting.OUTPUT).iterdir() if p.is_file()}
    edit(snapshot, reporting.STATUS, 'Scenario count: 150.', 'Scenario count: 0.')
    assert reporting.check(snapshot, write=True) == []
    first = (snapshot / reporting.REPORT).read_bytes()
    assert reporting.check(snapshot, write=True) == []
    assert first == (snapshot / reporting.REPORT).read_bytes()
    assert reporting.check(snapshot) == []
    assert before == {p.name: p.read_bytes() for p in (snapshot / reporting.OUTPUT).iterdir() if p.is_file()}


def test_duplicate_results_rejected():
    with pytest.raises(ValueError, match='duplicate'):
        reporting.index([{'scenario_id': 'x'}] * 2, ['scenario_id'])


def test_reordered_source_rows_do_not_change_summary(snapshot):
    path = snapshot / reporting.OUTPUT / 'results.csv'
    lines = path.read_text().splitlines()
    path.write_text('\n'.join([lines[0], *reversed(lines[1:])]) + '\n')
    assert reporting.check(snapshot) == []
