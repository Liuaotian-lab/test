"""Universal chart detection using generic image features (no hardcoded thresholds per problem)."""
import numpy as np
import cv2


def detect_chart_regions(image: np.ndarray, min_rel_area: float = 0.01) -> list[dict]:
    """
    Detect chart sub-regions in a page image using sliding window.
    
    Uses 3 generic features:
      1. Edge density (Canny)
      2. Long straight lines (HoughLinesP)
      3. Text coverage (MSER)
    
    Args:
        image: RGB numpy array (H, W, 3)
        min_rel_area: minimum chart area relative to total page
    
    Returns:
        List of {'bbox': (x,y,w,h), 'type': str, 'score': float, 'features': {...}}
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape[:2]
    page_area = h * w

    # Sliding window parameters
    win_size = min(h, w, 512)
    step = win_size // 2

    candidates = []
    seen = set()

    for y in range(0, h - win_size // 2, step):
        for x in range(0, w - win_size // 2, step):
            y2 = min(y + win_size, h)
            x2 = min(x + win_size, w)
            region = gray[y:y2, x:x2]
            result = _classify_region(region, page_area)
            if result and result['score'] > 0.35:
                key = (x // step, y // step)
                if key not in seen:
                    seen.add(key)
                    candidates.append({
                        'bbox': (x, y, x2 - x, y2 - y),
                        'type': result['type'],
                        'score': result['score'],
                        'features': result['features'],
                    })

    # Non-maximum suppression: merge overlapping high-score windows
    merged = _nms_merge(candidates, iou_threshold=0.3)
    return sorted(merged, key=lambda c: c['score'], reverse=True)


def _classify_region(gray: np.ndarray, page_area: int) -> dict | None:
    """Classify a single image region using generic visual features."""
    rh, rw = gray.shape[:2]
    rel_area = (rh * rw) / page_area
    
    if rel_area < 0.005:
        return None

    # Feature 1: Edge density
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / (rh * rw)

    # Feature 2: Long straight lines (axis candidates)
    min_line_len = min(rh, rw) * 0.15
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=50,
                            minLineLength=max(20, int(min_line_len)), maxLineGap=10)
    n_long_lines = len(lines) if lines is not None else 0

    # Feature 3: Text coverage via MSER
    try:
        mser = cv2.MSER_create()
        mser_regions, _ = mser.detectRegions(gray)
        text_area = sum(cv2.contourArea(np.array(pts).reshape(-1, 1, 2))
                        for pts in mser_regions) if mser_regions else 0
        text_coverage = text_area / (rh * rw)
    except Exception:
        text_coverage = 0.0

    # Composite score
    score = edge_density * 3.0 + min(n_long_lines / 5.0, 1.0) * 4.0 - text_coverage * 2.0

    if score < 0.25:
        return None

    # Classify type
    if n_long_lines >= 2:
        chart_type = 'line_chart' if edge_density > 0.02 else 'diagram_with_axes'
    elif n_long_lines >= 1:
        chart_type = 'possible_chart'
    else:
        chart_type = 'unknown_chart'

    return {
        'type': chart_type,
        'score': round(score, 3),
        'features': {
            'edge_density': round(edge_density, 4),
            'n_long_lines': n_long_lines,
            'text_coverage': round(text_coverage, 4),
            'rel_area': round(rel_area, 4),
        }
    }


def _nms_merge(candidates: list[dict], iou_threshold: float = 0.3) -> list[dict]:
    """Merge overlapping bounding boxes using non-maximum suppression."""
    if len(candidates) <= 1:
        return candidates

    # Sort by score descending
    candidates.sort(key=lambda c: c['score'], reverse=True)
    merged = []

    while candidates:
        best = candidates.pop(0)
        best_box = best['bbox']

        # Find overlapping candidates
        remaining = []
        for c in candidates:
            iou = _box_iou(best_box, c['bbox'])
            if iou > iou_threshold:
                # Merge: expand best to include this one
                best_box = _union_box(best_box, c['bbox'])
            else:
                remaining.append(c)

        best['bbox'] = best_box
        merged.append(best)
        candidates = remaining

    return merged


def _box_iou(a: tuple, b: tuple) -> float:
    """Intersection over Union of two bounding boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    a_area = aw * ah
    b_area = bw * bh
    if a_area == 0 or b_area == 0:
        return 0.0
    
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    return inter / (a_area + b_area - inter)


def _union_box(a: tuple, b: tuple) -> tuple:
    """Union of two bounding boxes."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x = min(ax, bx)
    y = min(ay, by)
    w = max(ax + aw, bx + bw) - x
    h = max(ay + ah, by + bh) - y
    return (x, y, w, h)
