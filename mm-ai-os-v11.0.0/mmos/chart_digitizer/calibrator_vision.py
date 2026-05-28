"""Vision-based axis calibration: generates task cards for multi-modal Agent."""
import json
import os
from pathlib import Path
from mmos.kernel.jsonio import write_json
from mmos.kernel.events import now_iso


def generate_calibration_task(case_dir, figure_label, chart_image_path, raw_data_path, output_dir=None):
    """
    Generate a calibration task for a multi-modal Agent.
    
    The task includes:
    1. Path to the clean chart image (for reading axis labels)
    2. Path to the overlaid extraction debug image (for verifying curve quality)
    3. Structured questions about axis ranges, units, and curve quality
    
    The multi-modal Agent reads the chart image, answers the questions,
    and the calibration is applied to map pixel→data coordinates.
    
    Returns the path to the calibration task JSON.
    """
    case_dir = Path(case_dir)
    if output_dir is None:
        output_dir = case_dir / 'workspace' / 'chart_data'

    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Load raw pixel data  
    raw_data = json.load(open(raw_data_path)) if os.path.exists(raw_data_path) else {}
    points = raw_data.get('data_points', [])
    px_vals = [p['pixel_x'] for p in points] if points else []
    py_vals = [p['pixel_y'] for p in points] if points else []
    
    task = {
        'task_type': 'chart_axis_calibration',
        'figure': figure_label,
        'status': 'pending_calibration',
        'created_at': now_iso(),
        
        # Images for multi-modal review
        'images': {
            'clean_chart': str(chart_image_path) if chart_image_path else None,
            'extraction_overlay': None,  # Set by debug_viz
        },
        
        # Pixel data summary
        'pixel_data': {
            'x_pixel_range': [min(px_vals), max(px_vals)] if px_vals else None,
            'y_pixel_range': [min(py_vals), max(py_vals)] if py_vals else None,
            'point_count': len(points),
        },
        
        # Questions the Agent needs to answer
        'calibration_questions': [
            {
                'id': 'x_axis_label',
                'question': 'X轴（横轴）的物理量是什么？单位是什么？',
                'expected_type': 'string',
            },
            {
                'id': 'x_axis_range',
                'question': 'X轴的数值范围是多少？(最小值, 最大值)',
                'expected_type': 'list[float, float]',
            },
            {
                'id': 'y_axis_label',
                'question': 'Y轴（纵轴）的物理量是什么？单位是什么？',
                'expected_type': 'string',
            },
            {
                'id': 'y_axis_range',
                'question': 'Y轴的数值范围是多少？(最小值, 最大值)',
                'expected_type': 'list[float, float]',
            },
            {
                'id': 'curve_quality',
                'question': '提取的曲线点是否与图上的曲线一致？有无明显偏差或噪声？',
                'expected_type': 'string',
                'options': ['good', 'minor_noise', 'poor_quality'],
            },
        ],
        
        # To be filled by the multi-modal Agent
        'calibration_result': None,
        
        # Auto-calibration note
        'note': 'If no multimodal Agent is available, provide axis ranges manually via chart-digitize --calibrate-x "min,max" --calibrate-y "min,max"',
    }
    
    task_path = output_dir / f'{figure_label}_calibration_task.json'
    write_json(task_path, task)
    
    return {
        'task_path': str(task_path),
        'task': task,
        'message': f'Calibration task created. Review the chart image and answer the {len(task["calibration_questions"])} questions.',
    }


def apply_calibration(raw_data_path, x_range, y_range, output_path):
    """Apply axis calibration: remap pixel->data coordinates."""
    raw_data = json.load(open(raw_data_path))
    points = raw_data.get('data_points', [])
    
    px_vals = [p['pixel_x'] for p in points]
    py_vals = [p['pixel_y'] for p in points]
    
    if not px_vals or not py_vals:
        return {'status': 'failed', 'reason': 'no_points'}
    
    px_min, px_max = min(px_vals), max(px_vals)
    py_min, py_max = min(py_vals), max(py_vals)
    
    x_min, x_max = x_range[0], max(x_range[1], x_range[0] + 1e-6)
    y_min, y_max = y_range[0], max(y_range[1], y_range[0] + 1e-6)
    
    calibrated_points = []
    for p in points:
        dx = (p['pixel_x'] - px_min) / (px_max - px_min)
        dy = (p['pixel_y'] - py_min) / (py_max - py_min)
        calibrated_points.append({
            'x': round(x_min + dx * (x_max - x_min), 5),
            'y': round(y_min + dy * (y_max - y_min), 5),
            'confidence': p.get('confidence', 0),
        })
    
    output = {
        'figure': raw_data.get('figure_id', 'unknown'),
        'calibration': {'x_range': x_range, 'y_range': y_range},
        'point_count': len(calibrated_points),
        'data_points': calibrated_points,
        'status': 'calibrated',
    }
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    write_json(output_path, output)
    return output
