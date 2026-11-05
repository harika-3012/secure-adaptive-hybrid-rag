"""CLI: run the preliminary retrieval evaluation.

    cd backend && .venv\\Scripts\\activate && cd .. && python experiments/evaluation.py --k 5

Writes CSV/JSON/PNG into experiments/results/.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

import pandas as pd  # noqa: E402

from app.services.embedding_service import EmbeddingService  # noqa: E402
from app.services.evaluation_service import EvaluationService  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--alpha", type=float, default=None, help="fixed-hybrid alpha (default from config)")
    args = ap.parse_args()

    result = EvaluationService(EmbeddingService()).run(args.k, args.alpha)
    pd.set_option("display.width", 160)
    print(f"\n[{result['status']}] {result['caveat']}\n")
    print(pd.DataFrame(result["overall"]).round(3).to_string(index=False))
    print("\nEvidence gate:\n", pd.DataFrame(result["evidence_gate"]).round(3).to_string(index=False))
    print(f"\nSaved to {ROOT / 'experiments' / 'results'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
