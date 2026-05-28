"""PDF → PNG conversion with page-level metadata."""
import os
from pathlib import Path
from pdf2image import convert_from_path


def pdf_to_images(pdf_path: Path, dpi: int = 200) -> list[dict]:
    """Convert PDF pages to PNG images and save them.
    
    Returns list of {'page_num': int, 'image': PIL.Image, 'path': str, 'size': (w,h)}
    """
    pdf_path = Path(pdf_path)
    output_dir = pdf_path.parent.parent.parent / 'workspace' / 'chart_data' / 'pages'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    images = convert_from_path(str(pdf_path), dpi=dpi)
    results = []
    
    for i, img in enumerate(images):
        fname = f"{pdf_path.stem}_page_{i+1}.png"
        out_path = output_dir / fname
        img.save(str(out_path))
        results.append({
            'page_num': i + 1,
            'path': str(out_path),
            'size': img.size,
            'dpi': dpi,
        })
    
    return results


def docx_images_to_png(docx_path: Path, output_dir: Path = None) -> list[dict]:
    """Extract embedded images from DOCX file. Uses zipfile internally."""
    import zipfile
    from PIL import Image
    import io
    
    docx_path = Path(docx_path)
    if output_dir is None:
        output_dir = docx_path.parent.parent.parent / 'workspace' / 'chart_data' / 'docx_images'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    with zipfile.ZipFile(str(docx_path)) as z:
        for name in sorted(z.namelist()):
            if name.startswith('word/media/') and (name.endswith('.png') or name.endswith('.jpg') or name.endswith('.jpeg')):
                data = z.read(name)
                img = Image.open(io.BytesIO(data))
                fname = Path(name).name
                out_path = output_dir / fname
                img.save(str(out_path))
                results.append({
                    'source': str(docx_path),
                    'embedded_path': name,
                    'path': str(out_path),
                    'size': img.size,
                })
    return results
