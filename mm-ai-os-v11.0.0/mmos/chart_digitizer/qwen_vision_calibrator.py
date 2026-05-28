#!/usr/bin/env python3
"""
Qwen-VL Vision Calibrator — 阿里云百炼视觉模型对接模块

通过 OpenAI-compatible API 调用 qwen-vl-max 分析图表, 提取轴范围等结构化数据。

环境变量:
  DASHSCOPE_API_KEY  — 阿里云百炼 API Key
  DASHSCOPE_BASE_URL — 默认 https://dashscope.aliyuncs.com/compatible-mode/v1

用法:
  python3 mmos/chart_digitizer/qwen_vision_calibrator.py /path/to/chart.png
"""
import os, sys, json, base64
try:
    import urllib.request
except ImportError:
    import urllib.request as urllib


API_KEY = os.environ.get("DASHSCOPE_API_KEY", "sk-af04258f863a4838a3565a09be68b5b9")
BASE_URL = os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
MODEL = os.environ.get("DASHSCOPE_MODEL", "qwen-vl-max")


def image_to_base64(path):
    """Convert image file to base64 data URI."""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def calibrate_chart(image_path):
    """Use Qwen-VL to read chart axis ranges and data."""
    if not os.path.exists(image_path):
        return {"status": "failed", "error": f"File not found: {image_path}"}

    b64 = image_to_base64(image_path)
    ext = os.path.splitext(image_path)[1].lower().lstrip(".")
    mime = f"image/{ext}" if ext in ("png","jpg","jpeg","webp") else "image/png"
    data_uri = f"data:{mime};base64,{b64}"

    payload = {
        "model": MODEL,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": data_uri}},
                {"type": "text", "text": (
                    "Analyze this chart. Output ONLY valid JSON, no markdown, no explanation:\n"
                    '{\n'
                    '  "x_axis": {"label":"...", "min":float, "max":float, "unit":"..."},\n'
                    '  "y_axis": {"label":"...", "min":float, "max":float, "unit":"..."},\n'
                    '  "curve_description": "...",\n'
                    '  "estimated_peak": {"x":float, "y":float}\n'
                    '}'
                )}
            ]
        }]
    }

    url = f"{BASE_URL}/chat/completions"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )

    try:
        resp = urllib.request.urlopen(req, timeout=60)
        body = json.loads(resp.read().decode())
        content = body["choices"][0]["message"]["content"]
        # Strip markdown code fences if present
        if content.startswith("```"):
            content = content.split("\n",1)[1].rsplit("\n",1)[0]
        if content.startswith("json"):
            content = content[4:]
        result = json.loads(content)
        result["status"] = "success"
        result["model_used"] = MODEL
        return result
    except urllib.error.HTTPError as e:
        return {"status": "failed", "error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 qwen_vision_calibrator.py <chart_image_path>")
        sys.exit(1)
    result = calibrate_chart(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
