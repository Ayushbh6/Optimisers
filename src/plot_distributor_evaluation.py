"""Render every reserved nominal case, including regressions, without annualising."""
import argparse
import json
import os
from pathlib import Path

from src.demo_data.config import SCENARIO_FAMILIES
from src.demo_data.storage import validate_output
from src.evaluate_distributor import assess


def render(root: Path) -> Path:
    """Draw the registered service/investment trade-off and keep all cases visible."""
    root = validate_output(root)
    rows = []
    for path in sorted((root/'nominal').glob('*.json')):
        row = json.loads(path.read_text())
        if 'baseline' in row and 'optimiser' in row:
            rows.append(row)
    if len(rows) != 30:
        raise ValueError('Plot requires all 30 nominal cases, not a favourable subset')
    output = root/'tradeoffs.png'
    if output.exists():
        raise FileExistsError(output)
    # Keep Matplotlib's font/config cache inside this task's artifact directory.
    os.environ['MPLCONFIGDIR'] = str(root/'plot-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    gate = assess(rows)
    palette = ['#386cb0', '#d98324', '#7b4fa3', '#158477', '#9a5961', '#777777']
    labels = ['Ordinary trading', 'Restricted spending', 'Supplier disruption', 'Demand changes', 'Ageing stock', 'Ample stock']
    fig, ax = plt.subplots(figsize=(10, 6.5), layout='constrained')
    ax.set_facecolor('#fafaf8')
    for family, colour, label in zip(SCENARIO_FAMILIES, palette, labels):
        subset = [r for r in rows if r['family'] == family]
        x = [100*(r['optimiser']['settled']['investment_cents']/r['baseline']['settled']['investment_cents']-1) for r in subset]
        y = [100*(r['optimiser']['settled']['service']-r['baseline']['settled']['service']) for r in subset]
        ax.scatter(x, y, color=colour, s=55, alpha=.8, label=label, zorder=3)
        for xi, yi, row in zip(x, y, subset):
            case = next(c for c in gate['families'][family]['cases'] if c['seed'] == row['seed'])
            if case['qualifying']:
                ax.scatter([xi], [yi], facecolors='none', edgecolors='#111111', s=130, linewidths=1.1, zorder=4)
    ax.axhline(0, color='#555555', linewidth=.8)
    ax.axvline(0, color='#555555', linewidth=.8)
    for value in (2, -1, -5):
        ax.axhline(value, color='#aaaaaa', linestyle='--', linewidth=.8)
    for value in (-10, 5):
        ax.axvline(value, color='#aaaaaa', linestyle='--', linewidth=.8)
    ax.set_xlabel('Change in average stock + undelivered commitments (%)\nLeft means less inventory exposure; this is not profit or bank cash savings.')
    ax.set_ylabel('Change in on-time dispatch (percentage points)\nUp means more units dispatched by their requested date.')
    ax.set_title('Frozen candidate versus stock-cover ordering', loc='left', fontsize=16, pad=18)
    fig.suptitle('SYNTHETIC DATA · 30 reserved cases · 8 trading weeks per case', fontsize=10, color='#666666')
    ax.spines[['top', 'right']].set_visible(False)
    ax.legend(loc='best', fontsize=8, frameon=True, framealpha=.9)
    ax.grid(alpha=.12)
    fig.text(.01, -.04, 'Rings mark cases meeting a numerical improvement route plus expiry/end-stock checks.\nFamily consistency, complete-line service and severe-regression checks still determine the release gate.', fontsize=9)
    fig.savefig(output, dpi=160, bbox_inches='tight')
    plt.close(fig)
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    print(render(parser.parse_args().root))
