"""Handmade metric fixtures test gate logic, never demand an optimiser win."""
from copy import deepcopy

from src.demo_data.config import EVALUATION_SEEDS, SCENARIO_FAMILIES
from src.evaluate_distributor import assess, permitted_tail


def fixtures():
    """Fabricated numerical test records, not generated reserved business outcomes."""
    rows = []
    for family in SCENARIO_FAMILIES:
        for seed in EVALUATION_SEEDS:
            base = dict(service=.90, complete_line_service=.80, investment_cents=100000,
                        expiry_cents=0, ending_investment_cents=100000)
            candidate = {**base, 'investment_cents': 90000}
            rows.append(dict(family=family, seed=seed, baseline=dict(settled=base, audit_errors=[]),
                             optimiser=dict(settled=candidate, audit_errors=[])))
    return rows


def test_two_families_and_four_of_five_seeds_are_required():
    rows = fixtures()
    for row in rows:
        if row['family'] not in ('ordinary', 'restricted_spending'):
            row['optimiser']['settled']['investment_cents'] = 100000
    assert assess(rows)['quantitative_pass']
    for row in rows:
        if row['family'] == 'restricted_spending' and row['seed'] in EVALUATION_SEEDS[:2]:
            row['optimiser']['settled']['investment_cents'] = 100000
    assert not assess(rows)['quantitative_pass']


def test_ties_are_not_improvements_and_ample_does_not_qualify():
    rows = fixtures()
    for row in rows:
        row['optimiser']['settled'] = deepcopy(row['baseline']['settled'])
    result = assess(rows)
    assert not result['quantitative_pass']
    assert result['winning_families'] == []


def test_severe_service_regression_blocks_overall_headline():
    rows = fixtures()
    rows[-1]['optimiser']['settled']['service'] = .84
    result = assess(rows)
    assert not result['quantitative_pass']
    assert len(result['severe_regressions']) == 1


def test_expiry_and_terminal_commitments_cannot_be_hidden():
    rows = fixtures()
    for row in rows:
        row['optimiser']['settled']['ending_investment_cents'] = 105001
    assert not assess(rows)['quantitative_pass']
    assert permitted_tail(2500, 0)
    assert not permitted_tail(2501, 0)


def test_ledger_failure_blocks_even_favourable_metrics():
    rows = fixtures()
    rows[0]['optimiser']['audit_errors'] = ['corrupted stock movement']
    assert not assess(rows)['quantitative_pass']
