"""Bounded purchasing search where the physical warehouse judges every basket.

The search starts from the competent stock-cover basket.  It changes only
today's supplier basket, then recalculates every later stock-cover decision from
that candidate's evolving physical state.  It contains no allocation model,
shortage price, margin, or weighted business score.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import date
from math import ceil
from time import monotonic

from src.demo_data.utils import add_workdays

from .baseline import order_today
from .contracts import Alternative, ForecastBundle, PlanRequest, Purchase
from .patterns import historical_patterns
from .physical import validate_purchases
from .projection import planning_metrics, project
from .risk import demand_sensitivities


@dataclass(frozen=True)
class SearchBounds:
    """Explicit finite limits for one supplier-basket decision."""

    max_lines: int = 8
    case_steps: int = 1
    max_two_line_candidates: int = 8
    max_candidates: int = 40
    historical_views: int = 4

    def validate(self) -> None:
        """Reject accidental unbounded or empty searches."""
        values = asdict(self)
        if any(type(value) is not int or value < 1 for value in values.values()):
            raise ValueError('Discrete search bounds must be positive integers')
        if self.max_lines > 12 or self.case_steps > 3 or self.max_two_line_candidates > 24 or self.max_candidates > 80:
            raise ValueError('Discrete search bounds exceed the reviewed implementation limits')


def _signature(rows: list[Purchase]) -> tuple:
    return tuple(sorted((p.day, p.supplier, p.product, p.units) for p in rows))


def _today(rows: list[Purchase], day: date) -> list[Purchase]:
    return sorted((p for p in rows if p.day == day), key=lambda p: (p.supplier, p.product))


def _cash_cents(request: PlanRequest, rows: list[Purchase]) -> int:
    state = request.snapshot
    suppliers = {p.supplier for p in rows}
    return sum(p.units * state.term(p.supplier, p.product, p.day).cost for p in rows) + sum(
        state.suppliers[supplier].fee_cents for supplier in suppliers
    )


def _repair_supplier_minimum(request: PlanRequest, rows: list[Purchase], supplier: str,
                             *, avoid: tuple[str, ...] = ()) -> list[Purchase]:
    """Meet one supplier minimum by topping up an already-needed basket line."""
    state = request.snapshot
    basket = [p for p in rows if p.supplier == supplier]
    if not basket:
        return rows
    value = sum(p.units * state.term(p.supplier, p.product, p.day).cost for p in basket)
    missing = state.suppliers[supplier].minimum_cents - value
    if missing <= 0:
        return rows
    choices = []
    for line in basket:
        product = state.products[line.product]
        term = state.term(line.supplier, line.product, line.day)
        extra = ceil(missing / (product.case * term.cost)) * product.case
        choices.append((line.product in avoid, extra * term.cost, line.product, line, extra))
    _, _, _, selected, extra = min(choices, key=lambda row: row[:3])
    return [replace(line, units=line.units + extra) if line == selected else line for line in rows]


def _repair_minimums(request: PlanRequest, rows: list[Purchase], *, avoid: tuple[str, ...] = ()) -> list[Purchase]:
    result = list(rows)
    for supplier in sorted({p.supplier for p in result}):
        result = _repair_supplier_minimum(request, result, supplier, avoid=avoid)
    return sorted(result, key=lambda p: (p.supplier, p.product))


def _change_line(rows: list[Purchase], line: Purchase, units: int) -> list[Purchase]:
    result = [p for p in rows if p != line]
    if units:
        result.append(replace(line, units=units))
    return sorted(result, key=lambda p: (p.supplier, p.product))


def generate_baskets(request: PlanRequest, baseline_today: list[Purchase],
                     bounds: SearchBounds = SearchBounds()) -> tuple[list[dict], dict]:
    """Generate deterministic whole-case edits around today's baseline basket."""
    bounds.validate()
    state = request.snapshot
    baseline_today = _today(baseline_today, state.day)
    editable = [p for p in baseline_today if p.product not in request.locks][:bounds.max_lines]
    raw: list[tuple[str, list[Purchase], tuple[str, ...]]] = []

    for line in editable:
        raw.append((f'remove {line.product}', _change_line(baseline_today, line, 0), (line.product,)))
        case = state.products[line.product].case
        term = state.term(line.supplier, line.product, line.day)
        reduced = line.units - bounds.case_steps * case
        if reduced >= term.minimum:
            raw.append((f'reduce {line.product} by {bounds.case_steps} case(s)',
                        _change_line(baseline_today, line, reduced), (line.product,)))
        raw.append((f'increase {line.product} by {bounds.case_steps} case(s)',
                    _change_line(baseline_today, line, line.units + bounds.case_steps * case), ()))

    two_line = 0
    for left_index, left in enumerate(editable):
        for right in editable[left_index + 1:]:
            if two_line >= bounds.max_two_line_candidates:
                break
            left_case = state.products[left.product].case
            left_term = state.term(left.supplier, left.product, left.day)
            left_units = left.units - bounds.case_steps * left_case
            if left_units < left_term.minimum:
                left_units = 0
            right_case = state.products[right.product].case
            changed = _change_line(baseline_today, left, left_units)
            current_right = next(p for p in changed if p == right)
            changed = _change_line(changed, current_right,
                                   right.units + bounds.case_steps * right_case)
            raw.append((f'two-line: reduce {left.product}, increase {right.product}',
                        changed, (left.product,)))
            two_line += 1
        if two_line >= bounds.max_two_line_candidates:
            break

    baseline_signature = _signature(baseline_today)
    seen, generated, rejected = set(), [], []
    for reason, basket, avoid in raw:
        basket = _repair_minimums(request, basket, avoid=avoid)
        signature = _signature(basket)
        if signature == baseline_signature or signature in seen:
            continue
        seen.add(signature)
        errors = validate_purchases(state, basket)
        # Before exact replay, ensure each same-day receipt group could fit in
        # an empty warehouse. Actual occupied capacity is then enforced by the
        # physical engine as stock is shipped and receipts arrive.
        arrivals = {}
        for line in basket:
            arrival = add_workdays(line.day, state.suppliers[line.supplier].lead_days + request.settings.delay_workdays)
            arrivals[arrival] = arrivals.get(arrival, 0) + line.units * state.products[line.product].volume_ml
            try:
                state.term(line.supplier, line.product, line.day)
            except ValueError as exc:
                errors.append(str(exc))
        if any(volume > state.capacity_ml for volume in arrivals.values()):
            errors.append('Same-day receipt group cannot fit within warehouse capacity')
        if errors:
            rejected.append(dict(reason=reason, basket=_basket_rows(request, basket), conflicts=errors))
            continue
        generated.append(dict(reason=reason, purchases=basket, signature=signature))
        if len(generated) >= bounds.max_candidates:
            break
    return generated, dict(
        baseline_lines=len(baseline_today),
        editable_lines=len(editable),
        omitted_lines=max(0, len(baseline_today) - len(editable)),
        raw_candidates=len(raw),
        feasible_candidates=len(generated),
        preflight_rejections=rejected,
    )


def _basket_rows(request: PlanRequest, basket: list[Purchase]) -> list[dict]:
    state = request.snapshot
    return [dict(
        supplier=p.supplier,
        product=p.product,
        units=p.units,
        cases=p.units // state.products[p.product].case,
        unit_cost_cents=state.term(p.supplier, p.product, p.day).cost,
        line_cash_cents=p.units * state.term(p.supplier, p.product, p.day).cost,
        expected_arrival=str(add_workdays(p.day, state.suppliers[p.supplier].lead_days + request.settings.delay_workdays)),
    ) for p in basket]


def _changes(request: PlanRequest, baseline: list[Purchase], candidate: list[Purchase],
             generation_reason: str) -> list[dict]:
    state = request.snapshot
    before = {(p.supplier, p.product): p.units for p in baseline}
    after = {(p.supplier, p.product): p.units for p in candidate}
    output = []
    for supplier, product in sorted(before.keys() | after.keys()):
        old, new = before.get((supplier, product), 0), after.get((supplier, product), 0)
        if old != new:
            why = generation_reason if product in generation_reason else (
                'supplier-minimum repair using a product already needed in the baseline basket'
                if new > old else generation_reason
            )
            output.append(dict(supplier=supplier, product=product, baseline_units=old,
                               candidate_units=new, change_units=new-old,
                               case_size=state.products[product].case, reason=why))
    return output


def _delivery_losses(reference, candidate) -> list[dict]:
    if reference.state.demand.keys() != candidate.state.demand.keys():
        raise ValueError('Compared demand must be identical')
    losses = []
    for key, before in reference.state.demand.items():
        after = candidate.state.demand[key]
        if before.units != after.units:
            raise ValueError('Compared requested quantities must be identical')
        if after.on_time < before.on_time or after.shipped < before.shipped:
            losses.append(dict(line=key, customer=before.customer, product=before.product,
                               estimated=before.estimated,
                               on_time_change=after.on_time-before.on_time,
                               shipped_change=after.shipped-before.shipped))
    return losses


def _view_summary(before: dict, after: dict, losses: list[dict]) -> dict:
    return dict(
        baseline=before,
        candidate=after,
        delivery_losses=losses,
        booked_change=after['booked_fulfilled_units']-before['booked_fulfilled_units'],
        on_time_change=after['on_time_units']-before['on_time_units'],
        investment_change_cents=after['investment_cents']-before['investment_cents'],
        expiry_change_cents=after['expiry_cents']-before['expiry_cents'],
        ending_investment_change_cents=after['ending_investment_cents']-before['ending_investment_cents'],
    )


def adaptive_replay(request: PlanRequest, view: ForecastBundle,
                    today_basket: list[Purchase]) -> tuple[object, list[Purchase], int]:
    """Commit today's basket, then recalculate stock cover from evolved state.

    The demand view stays fixed and contains no evaluator outcomes. Only the
    operational state changes as receipts, dispatch and later baskets occur.
    The returned schedule is the exact set of purchases placed in this replay.
    """
    state, settings = request.snapshot, request.settings
    today_basket = _today(today_basket, state.day)
    purchases: list[Purchase] = []
    decision_count = 0

    def decide(current, shared_bundle):
        nonlocal decision_count
        if current.day == state.day:
            basket = list(today_basket)
        elif any(s.weekday == current.day.weekday() for s in current.suppliers.values()):
            basket = order_today(current, settings, bundle=view)
        else:
            basket = []
        if basket:
            decision_count += 1
            purchases.extend(basket)
        return basket

    replay = project(state, settings, [], bundle=view, policy=decide)
    schedule = sorted(purchases, key=lambda p: (p.day, p.supplier, p.product))
    return replay, schedule, decision_count


def optimise_basket(request: PlanRequest, bundle: ForecastBundle, baseline: list[Purchase],
                    bounds: SearchBounds = SearchBounds(), *, views: dict[str, ForecastBundle] | None = None
                    ) -> tuple[Alternative, dict]:
    """Replay every feasible basket and return the safest lower-stock survivor."""
    started = monotonic()
    bounds.validate()
    state, settings = request.snapshot, request.settings
    today_baseline = _today(baseline, state.day)
    generated, generation = generate_baskets(request, today_baseline, bounds)
    if views is None:
        views = {**demand_sensitivities(bundle),
                 **historical_patterns(state, bundle, blocks=bounds.historical_views)}
    history_count = sum(name.startswith('history-') for name in views)
    required = {'nominal', 'lower', 'higher'}
    if not required.issubset(views) or history_count != bounds.historical_views:
        reason = 'All nominal/lower/higher and four historical-pattern views are required'
        baseline_projection = project(state, settings, baseline, bundle=bundle)
        metrics = planning_metrics(baseline_projection, state, settings)
        return Alternative('Stock-cover comparison', baseline, metrics, 'validated', [reason]), dict(
            bounds=asdict(bounds), generation=generation, selected='Stock-cover comparison',
            candidate_outcomes=[], replay_count=1, elapsed_seconds=monotonic()-started,
            stopped_reason=reason, views={})

    references, reference_metrics, reference_schedules, reference_decisions = {}, {}, {}, {}
    for name, view in views.items():
        references[name], reference_schedules[name], reference_decisions[name] = adaptive_replay(
            request, view, today_baseline)
        reference_metrics[name] = planning_metrics(references[name], state, settings)

    outcomes, survivors, replay_count = [], [], len(views)
    for generated_index, generated_row in enumerate(generated):
        basket = generated_row['purchases']
        schedules = {}
        checks, rejected = {}, []
        for name, view in views.items():
            try:
                replay, schedules[name], candidate_decisions = adaptive_replay(request, view, basket)
                replay_count += 1
                measured = planning_metrics(replay, state, settings)
                losses = _delivery_losses(references[name], replay)
                before = reference_metrics[name]
                check = _view_summary(before, measured, losses)
                check['baseline_policy_decisions'] = reference_decisions[name]
                check['candidate_policy_decisions'] = candidate_decisions
                check['baseline_purchase_lines'] = len(reference_schedules[name])
                check['candidate_purchase_lines'] = len(schedules[name])
                if losses:
                    rejected.append(f'{name}: line-level delivery loss')
                if measured['booked_fulfilled_units'] < before['booked_fulfilled_units']:
                    rejected.append(f'{name}: booked fulfilment reduced')
                if measured['service'] + 1e-8 < before['service']:
                    rejected.append(f'{name}: service reduced')
                if measured['expiry_cents'] > before['expiry_cents']:
                    rejected.append(f'{name}: expiry increased')
                if measured['ending_investment_cents'] > before['ending_investment_cents']:
                    rejected.append(f'{name}: terminal stock plus commitments increased')
                checks[name] = check
            except ValueError as exc:
                rejected.append(f'{name}: {exc}')
                checks[name] = dict(valid=False, error=str(exc))
                break
        accepted = not rejected and len(checks) == len(views)
        row = dict(
            candidate_id=f'C{generated_index+1:02d}',
            generation_reason=generated_row['reason'],
            changes=_changes(request, today_baseline, basket, generated_row['reason']),
            basket=_basket_rows(request, basket),
            cash_required_cents=_cash_cents(request, basket),
            checks=checks,
            accepted=accepted,
            rejection_reasons=sorted(set(rejected)),
        )
        outcomes.append(row)
        if accepted:
            # Booked commitments and service are hard survivor conditions above.
            # Among safe choices, minimise mean investment, then expiry, charges,
            # and finally use the stable basket signature.
            investment = sum(check['candidate']['investment_cents'] for check in checks.values()) / len(checks)
            expiry = sum(check['candidate']['expiry_cents'] for check in checks.values())
            fees = checks['nominal']['candidate']['fees_cents']
            survivors.append((investment, expiry, fees, generated_row['signature'], row, schedules['nominal']))

    baseline_average = sum(row['investment_cents'] for row in reference_metrics.values()) / len(reference_metrics)
    improving = [row for row in survivors if row[0] < baseline_average - 1e-8]
    if improving:
        _, _, _, _, selected_row, selected_schedule = min(improving, key=lambda row: row[:4])
        selected_name = 'Simulation-checked basket'
        metrics = selected_row['checks']['nominal']['candidate']
        selected = Alternative(selected_name, selected_schedule, metrics,
                               'bounded discrete search; exact physical replay in seven views',
                               [selected_row['generation_reason']])
    else:
        selected_row, selected_schedule = None, baseline
        selected_name = 'Stock-cover comparison'
        selected = Alternative(selected_name, baseline, reference_metrics['nominal'], 'validated',
                               ['No lower-investment basket survived every physical replay'])

    view_report = {}
    for name, before in reference_metrics.items():
        alternatives = {}
        for row in outcomes:
            check = row['checks'].get(name, {})
            if 'candidate' not in check:
                continue
            alternatives[row['candidate_id']] = dict(
                metrics=check['candidate'],
                valid=True,
                preserves_service=check['candidate']['service'] >= before['service']-1e-8,
                preserves_booked=(check['candidate']['booked_fulfilled_units'] >=
                                  before['booked_fulfilled_units']),
                accepted=row['accepted'],
            )
        view_report[name] = dict(baseline=before, alternatives=alternatives)
    delivery_risks = []
    if selected_row is not None:
        for name, check in selected_row['checks'].items():
            candidate_metrics = check['candidate']
            booked_gap = candidate_metrics['booked_units']-candidate_metrics['booked_fulfilled_units']
            service_gap = candidate_metrics['requested_units']-candidate_metrics['on_time_units']
            if booked_gap:
                delivery_risks.append(f'{name}: {booked_gap} booked units remain unfulfilled in the projection')
            if service_gap:
                delivery_risks.append(f'{name}: {service_gap} requested units are not fulfilled on time')
    else:
        delivery_risks.append('No alternative passed every required view with lower average investment')
    report = dict(
        bounds=asdict(bounds),
        future_policy='adaptive stock cover recalculated from each replay state and demand view',
        generation=generation,
        required_views=list(views),
        reference_metrics=reference_metrics,
        candidate_outcomes=outcomes,
        survivors=len(survivors),
        improving_survivors=len(improving),
        selected=selected_name,
        selected_candidate=selected_row,
        selected_today_basket=_basket_rows(request, _today(selected_schedule, state.day)),
        selected_cash_required_cents=_cash_cents(request, _today(selected_schedule, state.day)),
        delivery_risks=delivery_risks,
        leftover_consequences=(None if selected_row is None else {
            name: {
                key: selected_row['checks'][name][key]
                for key in ('investment_change_cents', 'expiry_change_cents', 'ending_investment_change_cents')
            } for name in views
        }),
        replay_count=replay_count,
        elapsed_seconds=monotonic()-started,
        views=view_report,
    )
    return selected, report
