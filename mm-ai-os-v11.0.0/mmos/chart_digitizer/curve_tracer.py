"""Curve tracing: follow a line chart and extract (x,y) data points."""
import numpy as np
import cv2


def trace_curve(image: np.ndarray, bbox: tuple, axes: dict) -> list[dict]:
    """
    Trace a line curve within a chart's bounding box.
    
    Strategy:
    1. Crop to chart region
    2. For each column (x-position), find the curve's y-position
    3. Filter outliers and fill gaps
    4. Convert pixel coords → data coords
    5. Return point list with per-point confidence
    
    Returns:
        [{'x': data_x, 'y': data_y, 'pixel_std': float, 'confidence': float}, ...]
    """
    x, y, w, h = bbox
    region = image[y:y+h, x:x+w]
    gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY) if len(region.shape) == 3 else region
    
    # Detect the curve color: assume dark pixels on light background
    # Use Otsu thresholding to separate curve from background
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Get axis pixel ranges
    x_axis = axes.get('x_axis', {})
    y_axis = axes.get('y_axis', {})
    x_px = x_axis.get('pixel_range', [0, w])
    y_px = y_axis.get('pixel_range', [h, 0])
    
    x_data_range = x_axis.get('data_range', [0, 1])
    y_data_range = y_axis.get('data_range', [0, 1])
    
    # Trace column by column
    points = []
    num_cols = min(w, 200)  # Up to 200 sample columns
    col_width = max(1, w // num_cols)
    
    for col_idx in range(0, w, col_width):
        col_center = min(col_idx + col_width // 2, w - 1)
        column = binary[:, col_center:col_center+1].flatten() if col_center < w else binary[:, -1:].flatten()
        
        # Find dark pixels (curve) in this column
        curve_rows = np.where(column > 128)[0]
        
        if len(curve_rows) < 2:
            continue  # No curve in this column
            
        # Curve position = median of dark pixels
        pixel_y = float(np.median(curve_rows))
        pixel_std = float(np.std(curve_rows))
        
        # Confidence based on spread and pixel count
        confidence = 1.0 / (1.0 + pixel_std / 3.0) * min(1.0, len(curve_rows) / 8.0)
        
        # Convert pixel → data coordinates
        data_x = _pixel_to_data(col_center, x_px, x_data_range)
        data_y = _pixel_to_data(pixel_y, y_px, y_data_range)
        
        points.append({
            'x': round(data_x, 5),
            'y': round(data_y, 5),
            'pixel_x': col_center,
            'pixel_y': round(pixel_y, 1),
            'pixel_std': round(pixel_std, 2),
            'confidence': round(confidence, 3),
        })
    
    # Post-process: filter outliers by checking continuity
    if len(points) >= 3:
        points = _filter_continuity(points)
    
    return points


def _pixel_to_data(px: float, pixel_range: list, data_range: list) -> float:
    """Convert pixel coordinate to data value using linear mapping."""
    p0, p1 = pixel_range[0], pixel_range[1]
    d0, d1 = data_range[0], data_range[1]
    if abs(p1 - p0) < 1e-10:
        return d0
    ratio = (px - p0) / (p1 - p0)
    return d0 + ratio * (d1 - d0)


def _filter_continuity(points: list[dict], max_jump_ratio: float = 0.3) -> list[dict]:
    """Filter out points that deviate too far from neighbors."""
    if len(points) < 3:
        return points
    
    filtered = [points[0]]
    for i in range(1, len(points) - 1):
        prev_y = filtered[-1]['y']
        curr_y = points[i]['y']
        next_y = points[i+1]['y']
        
        # Expected y = average of neighbors
        expected = (prev_y + next_y) / 2
        if expected != 0:
            deviation = abs(curr_y - expected) / abs(expected)
            if deviation < max_jump_ratio:
                filtered.append(points[i])
            else:
                # Mark as interpolated with low confidence
                pt = dict(points[i])
                pt['y'] = round(expected, 5)
                pt['confidence'] = max(0.1, pt['confidence'] * 0.5)
                pt['interpolated'] = True
                filtered.append(pt)
        else:
            filtered.append(points[i])
    
    filtered.append(points[-1])
    return filtered
