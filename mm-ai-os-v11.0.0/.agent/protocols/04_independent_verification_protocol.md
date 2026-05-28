# 04 Independent Verification Protocol

Goal: avoid solver self-certification.

Verifier plugins must live under `engineering/questions/<QID>/verifiers/` and must not import the main solver. They should recompute core metrics from raw data or final outputs using independent formulas, sampling, optimization, or sanity bounds.

Required commands:

```bash
python scripts/mmtool.py verifier-run <case> --question <QID>
python scripts/mmtool.py verifier-compare <case> --question <QID> --strict
```
