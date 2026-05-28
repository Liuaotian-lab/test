"""v7 Chart Digitizer — synthetic regression tests for the pure distribution."""
import sys, os
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mmos.chart_digitizer.digitizer import chart_gaps
from mmos.chart_digitizer.chart_detector import detect_chart_regions
from mmos.chart_digitizer.axis_reader import read_axes


def test_chart_detection_line_chart():
    """Detector should find charts in a synthetic line chart image."""
    img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(img)
    draw.line([(100, 500), (700, 500)], fill='black', width=2)
    draw.line([(100, 100), (100, 500)], fill='black', width=2)
    for x_px in range(100, 700, 2):
        t = (x_px - 100) / 600
        y_px = 500 - int(t * t * 400)
        draw.ellipse([(x_px-1, y_px-1), (x_px+1, y_px+1)], fill='blue')
    arr = np.array(img)
    charts = detect_chart_regions(arr)
    assert len(charts) >= 1, f"Expected at least 1 chart, got {len(charts)}"
    assert charts[0]['type'] in ('line_chart', 'diagram_with_axes', 'possible_chart')


def test_chart_detection_text_only():
    """Text-only page should NOT be detected as chart."""
    img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(img)
    for i, line in enumerate(['Abstract', 'This paper studies...', '1. Introduction', 'We propose a model...']):
        draw.text((50, 50 + i * 60), line, fill='black')
    arr = np.array(img)
    charts = detect_chart_regions(arr)
    line_charts = [c for c in charts if c['type'] == 'line_chart']
    assert len(line_charts) == 0


def test_axis_detection():
    """Axis detection should find axes in a chart with clear axes."""
    img = Image.new('RGB', (800, 600), 'white')
    draw = ImageDraw.Draw(img)
    draw.line([(100, 500), (700, 500)], fill='black', width=2)
    draw.line([(100, 100), (100, 500)], fill='black', width=2)
    arr = np.array(img)
    axes = read_axes(arr, (0, 0, 800, 600))
    assert axes['status'] in ('found', 'partial')


def test_no_charts_case_produces_gaps_0(tmp_path):
    """A synthetic case with no figures should report gap_count=0."""
    case_dir = tmp_path / 'case_no_charts'
    (case_dir / 'workspace').mkdir(parents=True)
    (case_dir / 'data' / 'raw').mkdir(parents=True)
    (case_dir / 'registry').mkdir(parents=True)
    (case_dir / 'workspace' / 'problem_corpus.md').write_text('This problem has no figures. Only text and equations.', encoding='utf-8')
    (case_dir / 'workspace' / 'problem_graph.json').write_text('{"case_id":"test","questions":[]}', encoding='utf-8')
    (case_dir / 'registry' / 'questions_registry.json').write_text('{"case_id":"test","questions":[]}', encoding='utf-8')
    result = chart_gaps(case_dir)
    assert result['case_has_charts'] is False
    assert result.get('gap_count', 0) == 0


if __name__ == '__main__':
    import traceback
    tests = [test_chart_detection_line_chart, test_chart_detection_text_only, test_axis_detection]
    failed = 0
    for t in tests:
        try:
            t()
        except Exception:
            failed += 1
            traceback.print_exc()
    print(f"Results: {len(tests)-failed}/{len(tests)} passed")
    if failed:
        sys.exit(1)
    print('ALL PASSED')
