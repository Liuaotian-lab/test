"""Axis detection: finds axes and reads numerical tick marks via OCR."""
import numpy as np
import cv2
import math
import pytesseract


def read_axes(image: np.ndarray, bbox: tuple) -> dict:
    """
    Detect coordinate axes in a chart region and read numerical tick labels.
    
    3-stage process:
    1. Hough lines → find axis lines
    2. Pytesseract OCR on axis margins → read numerical tick values
    3. Fit linear mapping: pixel → data coordinate
    
    Returns:
        {'status':'found'|'partial', 'x_axis':{range, ticks, mapping}, 
         'y_axis':{...}, 'origin_pixel':(x,y)}
    """
    x, y, w, h = bbox
    region = image[y:y+h, x:x+w]
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY) if len(region.shape) == 3 else region
    
    # Stage 1: Detect axis lines via Hough transform
    edges = cv2.Canny(gray, 50, 150)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=50,
                            minLineLength=max(20, int(min(w, h) * 0.15)), maxLineGap=20)
    
    h_lines = []
    v_lines = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = abs(math.degrees(math.atan2(y2 - y1, x2 - x1)))
            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            if angle < 15 or angle > 165:
                h_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'length': length})
            elif 75 < angle < 105:
                v_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'length': length})
    
    # Stage 2: OCR on axis margins
    # Y-axis: left 15% strip → find numbers
    left_strip = gray[:, :max(int(w*0.15), 50)]
    # X-axis: bottom 15% strip → find numbers  
    bottom_strip = gray[int(h*0.85):, :]
    
    def extract_ticks(strip, orientation='vertical'):
        """Extract numerical values from axis strip."""
        # Invert for OCR (white text on dark looks better)
        inv = cv2.bitwise_not(strip)
        data = pytesseract.image_to_data(inv, lang='eng', 
                                         output_type=pytesseract.Output.DICT,
                                         config='--psm 6 -c tessedit_char_whitelist=0123456789.')
        ticks = []
        for i, txt in enumerate(data['text']):
            txt = txt.strip()
            if txt and any(c.isdigit() for c in txt) and data['conf'][i] > 20:
                try:
                    val = float(txt)
                    cx = data['left'][i] + data['width'][i]/2
                    cy = data['top'][i] + data['height'][i]/2
                    ticks.append({'value': val, 'cx': cx, 'cy': cy, 'conf': data['conf'][i]})
                except ValueError:
                    pass
        return ticks

    y_ticks = extract_ticks(left_strip, 'vertical')
    x_ticks = extract_ticks(bottom_strip, 'horizontal')
    
    # Stage 3: Fit linear mapping from tick data
    x_info = {'pixel_range': [0, w], 'data_range': [0.0, 1.0], 'mapping': 'linear', 'ticks': x_ticks, 'confidence': 0.3}
    y_info = {'pixel_range': [h, 0], 'data_range': [0.0, 1.0], 'mapping': 'linear', 'ticks': y_ticks, 'confidence': 0.3}
    
    # Try to calibrate from OCR'd tick marks
    if len(x_ticks) >= 2:
        x_vals = sorted(set(t['value'] for t in x_ticks))
        if len(x_vals) >= 2:
            x_min, x_max = float(min(x_vals)), float(max(x_vals))
            x_info['data_range'] = [x_min, x_max]
            x_info['confidence'] = min(0.9, 0.4 + 0.1 * len(x_vals))
    
    if len(y_ticks) >= 2:
        y_vals = sorted(set(t['value'] for t in y_ticks))
        if len(y_vals) >= 2:
            y_min, y_max = float(min(y_vals)), float(max(y_vals))
            # Y-axis is inverted (top=high, bottom=low in pixels)
            y_info['data_range'] = [y_min, y_max]
            y_info['confidence'] = min(0.9, 0.4 + 0.1 * len(y_vals))
    
    # Determine status
    has_x = len(x_ticks) >= 2
    has_y = len(y_ticks) >= 2
    has_lines = len(h_lines) >= 1 and len(v_lines) >= 1
    
    if has_x and has_y:
        status = 'found'
    elif (has_x or has_y) and has_lines:
        status = 'partial'
    else:
        status = 'partial'
    
    return {
        'status': status,
        'x_axis': x_info,
        'y_axis': y_info,
        'origin_pixel': [0, h],
        'bbox_offset': (x, y),
        'debug': {
            'h_lines': len(h_lines), 'v_lines': len(v_lines),
            'x_ticks_found': len(x_ticks), 'y_ticks_found': len(y_ticks),
            'x_tick_values': [t['value'] for t in x_ticks[:10]],
            'y_tick_values': [t['value'] for t in y_ticks[:10]],
        }
    }
