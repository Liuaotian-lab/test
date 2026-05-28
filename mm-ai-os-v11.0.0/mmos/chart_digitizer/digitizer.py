"""Main chart digitization orchestrator."""
import json
import re
from pathlib import Path
import numpy as np
import cv2

from mmos.kernel.jsonio import read_json, write_json
from mmos.kernel.events import now_iso
from .page_to_image import pdf_to_images, docx_images_to_png
from .chart_detector import detect_chart_regions
from .axis_reader import read_axes
from .curve_tracer import trace_curve


def chart_gaps(case_dir: Path) -> dict:
    """
    Analyze which figure references in the problem text lack data attachments.
    
    Returns a report listing figures that NEED chart-digitize extraction.
    Does NOT perform extraction itself.
    
    This is intended to be called during problem analysis, NOT during autopilot execution.
    The Agent reads this report and decides whether to invoke chart-digitize.
    """
    case_dir = Path(case_dir).resolve()
    data_dir = case_dir / 'data' / 'raw'
    workspace = case_dir / 'workspace'

    # 1. Read problem corpus and find figure references
    corpus_path = workspace / 'problem_corpus.md'
    corpus_text = ''
    if corpus_path.exists():
        corpus_text = corpus_path.read_text(encoding='utf-8', errors='ignore')

    # Find all "图N" and "Fig.N" references
    fig_refs = set()
    for m in re.finditer(r'图\s*(\d+)', corpus_text):
        fig_refs.add(f'图{m.group(1)}')
    for m in re.finditer(r'Fig\.?\s*(\d+)', corpus_text, re.I):
        fig_refs.add(f'图{m.group(1)}')  # Normalize to 图N

    if not fig_refs:
        return {'status': 'passed', 'case_has_charts': False, 'gaps': [], 'message': 'No figure references found in problem text.'}

    # 2. Check which figures have data attachments
    attachments = {}
    for f in sorted(data_dir.glob('*')):
        if re.match(r'附件\s*\d+', f.stem) or re.match(r'attachment\s*\d+', f.stem, re.I):
            num = re.search(r'(\d+)', f.stem)
            if num:
                attachments[f'int(num.group(1))'] = str(f.relative_to(case_dir))

    # 3. Determine which figures lack data
    gaps = []
    # Map: which figures correspond to which attachment numbers
    # Some figures are schematic while others require numeric digitization.
    # This mapping is NOT hardcoded — we detect from problem text context
    for fig in sorted(fig_refs):
        fig_num = int(re.search(r'(\d+)', fig).group(1))
        
        # Check if this figure has associated attachment  
        # Strategy: look for "附件N" near "图N" in text
        fig_idx = corpus_text.find(fig)
        if fig_idx < 0:
            fig_idx = corpus_text.find(fig.replace(' ', ''))
        
        nearby = corpus_text[max(0, fig_idx - 200):fig_idx + 200] if fig_idx >= 0 else ''
        has_attachment = any(re.search(rf'附件\s*{n}', nearby) for n in range(fig_num - 2, fig_num + 3) if n > 0)

        # Determine if it's likely a data-bearing chart
        is_schematic = any(w in corpus_text[max(0, fig_idx-50):min(len(corpus_text), fig_idx+80)]
                          for w in ['示意图', '原理', '结构图', 'schematic', 'diagram'])

        if not has_attachment and not is_schematic:
            gaps.append({
                'figure': fig,
                'figure_number': fig_num,
                'reason': 'no_attachment_found_and_not_marked_schematic',
                'context': nearby[:150] if nearby else '',
                'recommendation': f"Run 'chart-digitize --figure {fig}' to extract data from this figure's chart."
            })

    return {
        'status': 'passed',
        'case_has_charts': len(fig_refs) > 0,
        'figures_found': sorted(list(fig_refs)),
        'figures_with_gaps': [g['figure'] for g in gaps],
        'gaps': gaps,
        'gap_count': len(gaps),
    }


def digitize_charts(case_dir: Path, figure_label: str = None, dpi: int = 200, debug: bool = False) -> dict:
    """
    Extract numerical data from charts in problem PDFs.
    
    Args:
        case_dir: Case directory
        figure_label: Specific figure to extract (e.g., '图2'). If None, all.
        dpi: Rendering resolution
        debug: Whether to save annotated debug images
    
    Returns:
        {'status': 'passed'|'failed', 'charts_extracted': int, 'data_files': [...]}
    """
    case_dir = Path(case_dir).resolve()
    data_dir = case_dir / 'data' / 'raw'
    chart_dir = case_dir / 'workspace' / 'chart_data'
    ready_dir = chart_dir / 'ready'
    chart_dir.mkdir(parents=True, exist_ok=True)
    ready_dir.mkdir(parents=True, exist_ok=True)

    extracted = []

    # Process PDF files
    for pdf_path in sorted(data_dir.glob('*.pdf')):
        pages = pdf_to_images(pdf_path, dpi=dpi) if pdf_path.suffix.lower() == '.pdf' else []
        if not pages:
            continue

        for page_info in pages:
            img = cv2.imread(page_info['path'])
            if img is None:
                continue
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            # Detect charts
            charts = detect_chart_regions(img_rgb)

            for ci, chart in enumerate(charts):
                if chart['type'] not in ('line_chart', 'diagram_with_axes'):
                    continue

                # Try to read axes
                axes = read_axes(img_rgb, chart['bbox'])
                if axes['status'] != 'found':
                    continue

                # Trace curve
                points = trace_curve(img_rgb, chart['bbox'], axes)
                if len(points) < 5:
                    continue  # Too few points

                # Determine figure label
                fig_id = figure_label or f"chart_{len(extracted)+1}"

                # Compute overall confidence
                confidences = [p['confidence'] for p in points]
                overall_conf = round(float(np.mean(confidences)), 3) if confidences else 0.0

                # Try to auto-calibrate axis ranges from point bounds
                x_vals = [p['x'] for p in points]
                y_vals = [p['y'] for p in points]
                
                # Update axis data ranges
                chart['axes'] = axes
                # Auto-scale: set data range to actual extracted values
                if x_vals:
                    axes['x_axis']['data_range'] = [min(x_vals), max(x_vals)]
                if y_vals:
                    axes['y_axis']['data_range'] = [min(y_vals), max(y_vals)]

                # Build normalized output
                output = {
                    'figure_id': fig_id.replace(' ', '_'),
                    'source_file': str(pdf_path.relative_to(case_dir)),
                    'source_page': page_info['page_num'],
                    'chart_type': chart['type'],
                    'axes': axes,
                    'point_count': len(points),
                    'data_points': points,
                    'overall_confidence': overall_conf,
                    'status': 'good' if overall_conf > 0.6 else ('low_quality' if overall_conf > 0.4 else 'unreliable'),
                    'extraction_metadata': {
                        'dpi': dpi,
                        'algorithm_version': 'v1.0',
                        'extraction_time_utc': now_iso(),
                    }
                }

                # Save JSON
                json_path = chart_dir / f'{fig_id.replace(" ", "_")}.json' if figure_label else chart_dir / f'chart_{len(extracted)+1}.json'
                write_json(json_path, output)

                # Save CSV for easy solver import
                csv_path = ready_dir / f'{fig_id.replace(" ", "_")}.csv'
                with open(csv_path, 'w') as f:
                    f.write('x,y,confidence\n')
                    for p in points:
                        f.write(f'{p["x"]},{p["y"]},{p["confidence"]}\n')

                # Save Python module
                py_path = ready_dir / f'{fig_id.replace(" ", "_")}.py'
                with open(py_path, 'w') as f:
                    f.write(f'# Auto-generated chart data for {fig_id}\n')
                    f.write(f'# Source: {pdf_path.name}, page {page_info["page_num"]}\n')
                    f.write(f'# Extracted by chart_digitizer v1.0\n')
                    f.write('import numpy as np\n')
                    f.write(f'X_DATA = np.array({[p["x"] for p in points]})\n')
                    f.write(f'Y_DATA = np.array({[p["y"] for p in points]})\n')
                    f.write(f'CONFIDENCE = np.array({[p["confidence"] for p in points]})\n')
                    f.write(f'OVERALL_CONFIDENCE = {overall_conf}\n')

                extracted.append({
                    'figure_id': fig_id,
                    'json_path': str(json_path.relative_to(case_dir)),
                    'csv_path': str(csv_path.relative_to(case_dir)),
                    'points': len(points),
                    'confidence': overall_conf,
                })

                if debug:
                    _save_debug_image(img_rgb, chart['bbox'], axes, points, chart_dir, fig_id)

    return {
        'status': 'passed' if len(extracted) > 0 else 'warning',
        'case_id': case_dir.name,
        'charts_extracted': len(extracted),
        'data_files': extracted,
        'warnings': ['no_charts_found'] if not extracted else [],
    }


def _save_debug_image(img, bbox, axes, points, output_dir, fig_id):
    """Save annotated debug visualization."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    x, y, w, h = bbox
    region = img[y:y+h, x:x+w]

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.imshow(region)

    # Plot extracted points
    px_vals = [p['pixel_x'] for p in points]
    py_vals = [p['pixel_y'] for p in points]
    confs = [p['confidence'] for p in points]
    sizes = [5 + 20 * c for c in confs]
    ax.scatter(px_vals, py_vals, c='red', s=sizes, alpha=0.7, label='Extracted points')

    # Plot origin
    if axes.get('origin_pixel'):
        ox, oy = axes['origin_pixel']
        ax.plot(ox, oy, 'go', markersize=10, label='Origin')

    ax.set_title(f'{fig_id} — {len(points)} points extracted')
    ax.legend()
    
    debug_path = output_dir / 'debug' / f'{fig_id.replace(" ","_")}_annotated.png'
    debug_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(str(debug_path), dpi=100, bbox_inches='tight')
    plt.close(fig)
