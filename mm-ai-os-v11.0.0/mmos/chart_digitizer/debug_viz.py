"""Visualization: annotated debug images for chart extraction audit."""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def save_annotated_chart(pil_image, bbox, extracted_points, axes_info, output_path):
    """Save chart region with extracted points overlaid."""
    x, y, w, h = bbox
    region = np.array(pil_image.crop((x, y, x+w, y+h)))
    
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(region)
    
    if extracted_points:
        xs = [p['pixel_x'] for p in extracted_points]
        ys = [p['pixel_y'] for p in extracted_points]
        confs = [p['confidence'] for p in extracted_points]
        sizes = [3 + 12*c for c in confs]
        ax.scatter(xs, ys, c='red', s=sizes, alpha=0.6, label=f'extracted ({len(extracted_points)} pts)')
    
    # Plot axis lines if detected
    if axes_info and axes_info.get('status') == 'found':
        ox, oy = axes_info.get('origin_pixel', (0, 0))
        ax.plot(ox, oy, 'go', markersize=10, label='detected origin')
    
    ax.set_title(f'Chart extraction audit: {os.path.basename(output_path)}')
    ax.legend()
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(str(output_path), dpi=100, bbox_inches='tight')
    plt.close(fig)
    return str(output_path)


def save_calibration_review_image(pil_image, bbox, extracted_points, output_path):
    """Save a clean chart-only image for multi-modal review."""
    x, y, w, h = bbox
    region = np.array(pil_image.crop((x, y, x+w, y+h)))
    
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.imshow(region)
    # No overlays — clean for human/Agent reading
    ax.set_title('Chart for axis calibration')
    ax.axis('on')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(str(output_path), dpi=150, bbox_inches='tight')
    plt.close(fig)
    return str(output_path)
