"""Bounded buyer review of one supplier-line deferral, using physical replay only.

This is an exploratory feature, not a replacement production optimiser. Future
baseline purchases stay fixed; the only edit moves today's entire product line
to the supplier's following weekly order day. No quantities or terms are relaxed.
"""
from dataclasses import replace
from datetime import timedelta

from src.replenishment.contracts import PlanRequest, Purchase
from src.replenishment.forecast import forecast
from src.replenishment.planner import baseline_schedule
from src.replenishment.projection import project, planning_metrics
from src.replenishment.risk import demand_sensitivities
from src.replenishment.validation import validate_request


def defer_line(purchases: list[Purchase], line: Purchase) -> list[Purchase]:
    """Move an entire line by seven calendar days; merge any same-product line."""
    if purchases.count(line) != 1:
        raise ValueError('Deferral needs exactly one original purchase line')
    target = line.day + timedelta(days=7)
    result = [p for p in purchases if p != line]
    existing = [p for p in result if (p.day,p.supplier,p.product)==(target,line.supplier,line.product)]
    if existing:
        result.remove(existing[0])
        result.append(replace(existing[0],units=existing[0].units+line.units))
    else:
        result.append(replace(line,day=target))
    return sorted(result,key=lambda p:(p.day,p.supplier,p.product))


def repair_today_minimum(request: PlanRequest, purchases: list[Purchase], supplier_id: str) -> list[Purchase]:
    """Top up an existing line at least extra cost; never choose using outcomes.

    Empty baskets need no repair. No new product is invented as filler. This
    explicitly adds stock, which must still pass the same physical review.
    """
    state=request.snapshot
    basket=[p for p in purchases if p.day==state.day and p.supplier==supplier_id]
    value=sum(p.units*state.term(p.supplier,p.product).cost for p in basket)
    missing=state.suppliers[supplier_id].minimum_cents-value
    if not basket or missing<=0:return purchases
    choices=[]
    for p in basket:
        case=state.products[p.product].case;cost=state.term(p.supplier,p.product).cost
        units=((missing+case*cost-1)//(case*cost))*case
        choices.append((units*cost,p.product,p,units))
    _,_,line,units=min(choices,key=lambda x:x[:2])
    return [replace(p,units=p.units+units) if p==line else p for p in purchases]


def compare_dispatch(reference, candidate) -> list[dict]:
    """Disclose any line losing on-time or total fulfilment under the same requests."""
    if reference.state.demand.keys()!=candidate.state.demand.keys():
        raise ValueError('Compared demand must be identical')
    losses=[]
    for key,before in reference.state.demand.items():
        after=candidate.state.demand[key]
        if before.units!=after.units:
            raise ValueError('Compared requested quantities must be identical')
        if after.on_time<before.on_time or after.shipped<before.shipped:
            losses.append(dict(line=key,customer=before.customer,product=before.product,
                estimated=before.estimated,on_time_change=after.on_time-before.on_time,
                shipped_change=after.shipped-before.shipped))
    return losses


def review_purchase_lines(request: PlanRequest, *, max_lines: int=8, repair_minimum: bool=False, mode: str='defer') -> dict:
    """Review at most eight baseline lines once; no iterative or outcome-based search."""
    validate_request(request)
    if mode not in {'defer','replace'}:
        raise ValueError('Review mode must be defer or replace')
    if request.locks or request.excluded:
        raise ValueError('This bounded research screen does not support buyer locks or exclusions')
    if type(max_lines) is not int or not 1<=max_lines<=8:
        raise ValueError('Bounded screen supports one to eight lines')
    state,settings=request.snapshot,request.settings
    bundle=forecast(state,settings)
    baseline=baseline_schedule(request,bundle)
    views=demand_sensitivities(bundle)
    references={name:project(state,settings,baseline,bundle=view) for name,view in views.items()}
    today=sorted([p for p in baseline if p.day==state.day],key=lambda p:(p.supplier,p.product))
    rows=[]
    for line in today[:max_lines]:
        purchases=defer_line(baseline,line) if mode=='defer' else [p for p in baseline if p!=line]
        if repair_minimum:
            purchases=repair_today_minimum(request,purchases,line.supplier)
        checks={}
        for name,view in views.items():
            before=planning_metrics(references[name],state,settings)
            try:
                replay=project(state,settings,purchases,bundle=view)
                after=planning_metrics(replay,state,settings)
                losses=compare_dispatch(references[name],replay)
                checks[name]=dict(valid=True,baseline=before,candidate=after,delivery_losses=losses,
                    passes=not losses and after['expiry_cents']<=before['expiry_cents']
                    and after['ending_investment_cents']<=before['ending_investment_cents'])
            except ValueError as exc:
                checks[name]=dict(valid=False,passes=False,conflict=str(exc))
        nominal=checks['nominal']
        passes=all(c['passes'] for c in checks.values())
        reduction=nominal['baseline']['investment_cents']-nominal['candidate']['investment_cents'] if nominal['valid'] else None
        rows.append(dict(product=line.product,supplier=line.supplier,units=line.units,
            mode=mode,minimum_repair_enabled=repair_minimum,
            proposed_today=[dict(supplier=p.supplier,product=p.product,units=p.units) for p in purchases if p.day==state.day],
            original_day=str(line.day),proposed_day=str(line.day+timedelta(days=7)) if mode=='defer' else None,checks=checks,
            conditional_candidate=passes and reduction is not None and reduction>0,
            projected_average_investment_reduction_cents=reduction))
    return dict(input_hash=request.identity(),decision_day=str(state.day),synthetic=state.synthetic,
        conditional_projection_only=True,baseline_lines_today=len(today),reviewed_lines=len(rows),
        omitted_by_cap=max(0,len(today)-max_lines),trials=rows)


def review_deferrals(request: PlanRequest, *, max_lines: int=8, repair_minimum: bool=False) -> dict:
    """Compatibility entry point for the original bounded deferral screen."""
    return review_purchase_lines(request,max_lines=max_lines,repair_minimum=repair_minimum)
