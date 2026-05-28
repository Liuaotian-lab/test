"""
本地视觉 MCP — 零网络依赖
基于 pytesseract(chi_sim+eng) + OpenCV + chart_digitizer
提供规范的 JSON 输出供求解器和 Agent 使用

用法:
  python3 mmos/vision_mcp.py analyze-image /path/to/image.png
  python3 mmos/vision_mcp.py chart-calibrate /path/to/chart.png --x-range "0,2.5" --y-range "0,6"
  python3 mmos/vision_mcp.py chart-autocalibrate /path/to/chart.png
"""
import os, sys, json, argparse
os.environ['TESSDATA_PREFIX'] = '/sessions/gallant-bold-feynman/mnt/outputs/tessdata/'

import pytesseract
import cv2
import numpy as np
from PIL import Image


def cmd_analyze_image(args):
    """Analyze an image: detect charts, perform OCR, describe content."""
    img = cv2.imread(args.image)
    if img is None:
        return {'status': 'failed', 'error': f'Cannot read {args.image}'}
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = img.shape[:2]
    
    # OCR text
    text = pytesseract.image_to_string(Image.fromarray(rgb), lang='chi_sim+eng', config='--psm 6')
    
    # OCR data with coordinates
    data = pytesseract.image_to_data(Image.fromarray(rgb), lang='chi_sim+eng',
                                     output_type=pytesseract.Output.DICT, config='--psm 6')
    
    text_items = []
    for i, txt in enumerate(data['text']):
        if txt.strip() and data['conf'][i] > 20:
            text_items.append({
                'text': txt.strip(),
                'x': data['left'][i], 'y': data['top'][i],
                'w': data['width'][i], 'h': data['height'][i],
                'confidence': data['conf'][i],
            })
    
    # Chart detection via OpenCV
    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    line_density = float(np.mean(edges > 0))
    
    result = {
        'status': 'passed',
        'image_size': f'{w}x{h}',
        'text_items_found': len(text_items),
        'text_preview': text[:500],
        'chart_features': {
            'edge_density': round(line_density, 4),
            'likely_contains_chart': line_density > 0.005,
        },
        'text_items': text_items[:50],
    }
    return result


def cmd_chart_autocalibrate(args):
    """Automatically detect axis ranges from chart image using OCR."""
    img = cv2.imread(args.image)
    if img is None:
        return {'status': 'failed', 'error': f'Cannot read {args.image}'}
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    
    # Find axis ticks: look for numbers near left edge (Y) and bottom edge (X)
    y_strip = rgb[:, :int(w*0.12), :]
    x_strip = rgb[int(h*0.85):, :, :]
    
    # OCR for numeric values
    data = pytesseract.image_to_data(Image.fromarray(rgb), lang='chi_sim+eng',
                                     output_type=pytesseract.Output.DICT,
                                     config='-c tessedit_char_whitelist=0123456789. --psm 6')
    
    y_vals, x_vals = [], []
    for i, txt in enumerate(data['text']):
        txt = txt.strip()
        if txt and any(c.isdigit() for c in txt) and data['conf'][i] > 20:
            try:
                v = float(txt)
                cx, cy = data['left'][i], data['top'][i]
                if cx < w * 0.12:
                    y_vals.append(v)
                elif cy > h * 0.8:
                    x_vals.append(v)
            except: pass
    
    result = {'status': 'auto_calibrated', 'image_size': f'{w}x{h}'}
    if y_vals:
        result['y_axis'] = {'detected_ticks': sorted(set(y_vals)), 'range': [min(y_vals), max(y_vals)]}
    if x_vals:
        result['x_axis'] = {'detected_ticks': sorted(set(x_vals)), 'range': [min(x_vals), max(x_vals)]}
    return result


def cmd_calibrate_curve(args):
    """Load pixel curve + axis ranges → output calibrated data."""
    from mmos.chart_digitizer.curve_tracer import trace_curve
    from mmos.chart_digitizer.chart_detector import detect_chart_regions
    
    img = cv2.imread(args.image)
    if img is None:
        return {'status': 'failed', 'error': f'Cannot read {args.image}'}
    
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    
    if args.x_range:
        x_range = [float(x) for x in args.x_range.split(',')]
    else:
        x_range = [0, 1]
    if args.y_range:
        y_range = [float(y) for y in args.y_range.split(',')]
    else:
        y_range = [0, 1]
    
    charts = detect_chart_regions(rgb, min_rel_area=0.02)
    if not charts:
        return {'status': 'failed', 'error': 'No chart detected'}
    
    # Use the largest chart
    chart = max(charts, key=lambda c: c['bbox'][2]*c['bbox'][3])
    bbox = chart['bbox']
    
    axes = {
        'status': 'found',
        'x_axis': {'pixel_range': [0, bbox[2]], 'data_range': x_range, 'mapping': 'linear', 'confidence': 0.9},
        'y_axis': {'pixel_range': [bbox[3], 0], 'data_range': y_range, 'mapping': 'linear', 'confidence': 0.9},
        'origin_pixel': [0, bbox[3]],
        'bbox_offset': (bbox[0], bbox[1]),
    }
    
    points = trace_curve(rgb, bbox, axes)
    
    return {
        'status': 'success',
        'chart_type': chart['type'],
        'bbox': list(bbox),
        'point_count': len(points),
        'x_range': x_range,
        'y_range': y_range,
        'data_points': points[:200],  # limit to 200 points
        'overall_confidence': round(sum(p.get('confidence',0) for p in points)/len(points), 3) if points else 0,
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(prog='vision_mcp')
    sub = parser.add_subparsers(dest='cmd', required=True)
    
    s = sub.add_parser('analyze-image'); s.add_argument('image')
    s = sub.add_parser('chart-autocalibrate'); s.add_argument('image')
    s = sub.add_parser('calibrate-curve'); s.add_argument('image')
    s.add_argument('--x-range', default=None)
    s.add_argument('--y-range', default=None)
    
    args = parser.parse_args()
    
    if args.cmd == 'analyze-image':
        result = cmd_analyze_image(args)
    elif args.cmd == 'chart-autocalibrate':
        result = cmd_chart_autocalibrate(args)
    elif args.cmd == 'calibrate-curve':
        result = cmd_calibrate_curve(args)
    
    print(json.dumps(result, ensure_ascii=False, indent=2))
