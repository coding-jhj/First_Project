"""
버스 번호 OCR 평가 (실사 테스트셋).

  data/ocr_bus/images/*.jpg|png  — 실제 촬영 버스 사진 (가이드: 최소 ~20장 권장)
  data/ocr_bus/labels.csv        — 파일명,정답번호 (헤더 있음)

labels.csv 예:
  file,expected
  bus01.jpg,702
  bus02.jpg,N37

사용법 (프로젝트 루트):
  python tools/eval_bus_ocr.py

결과: results/bus_ocr_eval.md (누적)
"""
import csv
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def _normalize_expected(s: str) -> str:
    return "".join(s.split()).upper()


def _pred_match(pred: str | None, exp: str) -> bool:
    if pred is None:
        return False
    pe = _normalize_expected(pred)
    ee = _normalize_expected(exp)
    if ee.isdigit() and pe.isdigit():
        return ee == pe
    return ee == pe or ee in pe or pe in ee


def main() -> int:
    root = Path(__file__).parent.parent
    img_dir = root / "data" / "ocr_bus" / "images"
    labels_path = root / "data" / "ocr_bus" / "labels.csv"
    seed_path = root / "data" / "ocr_bus" / "labels_seed.csv"
    out_md = root / "results" / "bus_ocr_eval.md"

    if not img_dir.is_dir():
        img_dir.mkdir(parents=True, exist_ok=True)
        print(f"폴더를 만들었습니다: {img_dir}")
        print("실제 버스 사진을 넣고 labels.csv 를 작성한 뒤 다시 실행하세요.")
        print(f"예시: {root / 'data' / 'ocr_bus' / 'labels.csv.example'}")
        return 0

    def _load_labels(csv_path: Path) -> list[tuple[str, str]]:
        out: list[tuple[str, str]] = []
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            r = csv.DictReader(f)
            for row in r:
                fn = (row.get("file") or row.get("filename") or "").strip()
                ex = (row.get("expected") or row.get("label") or "").strip()
                if fn and ex:
                    out.append((fn, ex))
        return out

    rows: list[tuple[str, str]] = []
    used_path: Path = labels_path
    if labels_path.is_file():
        rows = _load_labels(labels_path)
    if not rows and seed_path.is_file():
        rows = _load_labels(seed_path)
        used_path = seed_path
        print(
            "⚠️ labels_seed.csv 로 평가합니다 (expected 가 OCR 자동 추측이면 수치는 참고만 하세요).\n"
            "   검수 후 labels.csv 로 저장하는 것을 권장합니다.\n"
        )

    if not rows:
        print(f"labels 없음: {labels_path} 또는 {seed_path}")
        print("python tools/seed_bus_ocr_labels.py 또는 labels.csv.example 참고.")
        return 0

    try:
        from src.ocr.bus_ocr import recognize_bus_number
    except ImportError as e:
        print(f"EasyOCR 등 의존성 오류: {e}")
        return 1

    exts = {".jpg", ".jpeg", ".png", ".webp"}
    results: list[dict] = []
    fail_reason = defaultdict(int)

    for filename, expected in rows:
        p = img_dir / filename
        if not p.is_file():
            results.append({"file": filename, "expected": expected, "pred": None, "ok": False})
            fail_reason["missing_file"] += 1
            continue
        data = p.read_bytes()
        try:
            pred = recognize_bus_number(data, None)
        except Exception as e:
            pred = None
            fail_reason[f"exception:{e!s:.80}"] += 1
        ok = _pred_match(pred, expected)
        results.append({"file": filename, "expected": expected, "pred": pred, "ok": ok})
        if not ok:
            if pred is None:
                fail_reason["null_pred"] += 1
            else:
                fail_reason["mismatch"] += 1

    n = len(results)
    correct = sum(1 for r in results if r["ok"])
    acc = round(100.0 * correct / n, 1) if n else 0.0

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    try:
        label_disp = used_path.relative_to(root)
    except ValueError:
        label_disp = used_path
    block = f"""
---

## 버스 OCR 평가 — {now}

- 라벨 파일: `{label_disp}`
- 이미지 수(라벨 행): **{n}**
- 정확 일치(유연 매칭): **{correct}/{n} ({acc}%)**

### 실패 유형 히스토그램
{chr(10).join(f'- {k}: {v}' for k, v in sorted(fail_reason.items(), key=lambda x: -x[1]))}

### 개별 결과
| 파일 | 정답 | 예측 | 통과 |
|------|------|------|------|
{chr(10).join(
    f"| `{r['file']}` | {r['expected']} | {r['pred']} | {'✅' if r['ok'] else '❌'} |"
    for r in results
)}

"""
    out_md.parent.mkdir(parents=True, exist_ok=True)
    prev = out_md.read_text(encoding="utf-8") if out_md.exists() else ""
    out_md.write_text(prev + block, encoding="utf-8")
    print(f"정확도 {acc}% ({correct}/{n}) — 기록: {out_md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
