# MM-AI OS 7.4.0-candidate-official-split 安装与验证指南

当前版本：`7.4.0-candidate-official-split`

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
python setup_verify.py
python scripts/check_version_consistency.py
python scripts/run_tests.py --tier smoke
```

常用命令：

```bash
python scripts/mmtool.py case-init demo_case
python scripts/mmtool.py ingest-documents demo_case
python scripts/mmtool.py problem-parse-v2 demo_case
python scripts/mmtool.py problem-signature-extract demo_case
python scripts/mmtool.py academic-search demo_case --budget full
```
