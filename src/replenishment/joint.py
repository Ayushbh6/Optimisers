"""Generate and independently replay a shared purchase schedule across demand views."""
from .contracts import Alternative, ForecastBundle, PlanRequest, Purchase
from .projection import project, planning_metrics
from .solver import solve_joint


def joint_alternative(request: PlanRequest, views: dict[str, ForecastBundle],
                      baseline: list[Purchase]) -> tuple[Alternative | None, dict]:
    """Use one bounded model correction, never a search through evaluator outcomes."""
    state, settings = request.snapshot, request.settings
    reference = {name: planning_metrics(project(state, settings, baseline, bundle=bundle), state, settings)
                 for name, bundle in views.items()}
    targets = {name: row['service'] for name, row in reference.items()}
    statuses = []
    for attempt in range(2):
        purchases, status = solve_joint(request, views, targets)
        statuses.append(status)
        if not status['available']:
            return None, dict(statuses=statuses, reference=reference, accepted=False)
        try:
            measured = {name: planning_metrics(project(state, settings, purchases, bundle=bundle), state, settings)
                        for name, bundle in views.items()}
        except ValueError as exc:
            return None, dict(statuses=statuses, accepted=False, error=str(exc))
        missed = {name for name in views if measured[name]['service']+1e-8 < reference[name]['service']}
        if not missed:
            return Alternative('Historical order-pattern proposal', purchases, measured['nominal'],
                'primary model optimum; replay validated' if status['status']==0 else 'time-limited; replay validated',
                [str(status)]), dict(statuses=statuses, reference=reference, measured=measured, accepted=True)
        if attempt == 0:
            for name in missed:
                gap = reference[name]['service']-measured[name]['service']
                targets[name] = min(1.0, targets[name]+gap+1/max(1, measured[name]['requested_units']))
    return None, dict(statuses=statuses, reference=reference, measured=measured, accepted=False,
                      reason='Shared physical dispatch did not preserve every reference service target')
