"""
data/test_images_conditions/<조건>/<한글클래스>/ 구조에 대해 조건별 P/R/F1/FPR 요약.

각 조건 디렉터리는 tools/benchmark.py 의 bench_precision_recall 과 동일한
하위 구조(클래스별 폴더)를 가져야 한다.

사용:
  python tools/benchmark_conditions.py

결과: results/condition_eval.md
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
_TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(_TOOLS))
import benchmark as bm  # noqa: E402

BASE = Path("data/test_images_conditions")


def main() -> int:
    bench_precision_recall = bm.bench_precision_recall

    root = ROOT
    base = root / BASE
    out_md = root / "results" / "condition_eval.md"

    if not base.is_dir():
        print(f"폴더 없음: {base} — python tools/build_condition_test_images.py")
        return 1

    cond_dirs = sorted(d for d in base.iterdir() if d.is_dir())
    if not cond_dirs:
        print("조건 하위 폴더가 비었습니다.")
        return 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    blocks = [f"\n---\n\n## 조건별 탐지 지표 — {now}\n\n"]

    for cond in cond_dirs:
        prf = bench_precision_recall(str(cond))
        if "error" in prf:
            blocks.append(f"### `{cond.name}`\n- 오류: {prf['error']}\n\n")
            continue

        blocks.append(f"### 조건: `{cond.name}`\n\n")
        blocks.append(
            f"- 평균: R={prf['avg_recall']}% / P={prf['avg_precision']}% / "
            f"F1={prf['avg_f1']}% / FPR={prf['avg_fpr']}%\n\n"
        )
        top = prf.get("high_fpr_top") or []
        if top:
            blocks.append("**FPR 상위 클래스:** " + ", ".join(f"{x['class']}({x['fpr']}%)" for x in top[:5]) + "\n\n")

        per = prf.get("per_class") or {}
        blocks.append("| 클래스 | R% | P% | F1% | FPR% | TP | FP | FN |\n|---|---|---|---|---|---|---|---|\n")
        for cls_name, m in sorted(per.items()):
            blocks.append(
                f"| {cls_name} | {m['recall']} | {m['precision']} | {m['f1']} | {m['fpr']} | "
                f"{m['tp']} | {m['fp']} | {m['fn']} |\n"
            )
        blocks.append("\n")

    text = "".join(blocks)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    prev = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
    out_md.write_text(prev + text, encoding="utf-8")
    print(text)
    print(f"저장: {out_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
