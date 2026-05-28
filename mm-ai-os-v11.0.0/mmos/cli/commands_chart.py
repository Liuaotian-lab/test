from __future__ import annotations

from .commands_common import *
from .commands_common import _render_recommendation_md, render_run_report, _autopilot_step

def cmd_chart_gaps(args, osp):
    print_json(chart_gaps(osp.case_dir(args.case)))

def cmd_chart_digitize(args, osp):
    print_json(digitize_charts(osp.case_dir(args.case), figure_label=args.figure, dpi=args.dpi, debug=args.debug))

def cmd_chart_status(args, osp):
    case_dir = osp.case_dir(args.case)
    chart_dir = case_dir / 'workspace' / 'chart_data'
    files = list(chart_dir.glob('*.json')) if chart_dir.exists() else []
    print_json({
        'case_id': args.case,
        'charts_extracted': len(files),
        'files': [str(f.relative_to(case_dir)) for f in files],
    })

def cmd_chart_vision_calibrate(args, osp):
    case_dir = osp.case_dir(args.case)
    img_path = args.image
    if not os.path.isabs(img_path):
        img_path = os.path.join(str(case_dir), img_path)
    if not os.path.exists(img_path):
        print_json({'status':'failed','error':f'Image not found: {img_path}'})
        return
    result = calibrate_chart(img_path)
    if result.get('status') == 'success' and args.save:
        save_path = case_dir / 'workspace' / 'chart_data' / 'vision_calibration.json'
        save_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        json.dump(result, open(str(save_path),'w'), ensure_ascii=False, indent=2)
        result['saved_to'] = str(save_path.relative_to(case_dir))
    print_json(result)
