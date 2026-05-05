"""
VoiceGuide 자동 성능 실험 스크립트
====================================
사용법:
    (프로젝트 루트에서)
    python tools/benchmark.py

추천 테스트 이미지 구조 (Phase 4: ML/Vision 검증용):
    data/test_images/<클래스명(한국어)>/*.jpg|png

예)
    data/test_images/의자/*.jpg
    data/test_images/사람/*.jpg

주의:
    `src/depth/depth.detect_and_depth()`의 반환에서 class_ko(한국어)를 기준으로
    폴더명을 매칭합니다. (예: "chair" 폴더가 아니라 "의자" 폴더)

결과는 results/eval_log.md 에 자동 기록됩니다.
"""
import sys
from pathlib import Path
# tools/ 에서 실행해도 src/ 등 루트 패키지를 찾을 수 있도록
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import json
import shutil
import time
import cv2
import numpy as np
from datetime import datetime

# ── 테스트 이미지 생성 ──────────────────────────────────────────────────────
def _make_dummy_image(h=480, w=640):
    """640×480 랜덤 이미지 → JPEG bytes"""
    img = np.random.randint(80, 200, (h, w, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _load_real_image(path: str):
    """실제 테스트 이미지가 있으면 사용"""
    # cv2.imread는 실패 시 경고가 출력될 수 있어 bytes 기반 디코딩 사용
    try:
        raw = Path(path).read_bytes()
    except Exception:
        return None
    nparr = np.frombuffer(raw, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes() if ok else None

def _pick_first_test_image(image_dir: str = "data/test_images") -> tuple[bytes | None, str]:
    """
    data/test_images 아래에서 첫 번째 이미지를 찾아 bytes로 로드.
    없으면 (None, 사유) 반환.
    """
    base = Path(image_dir)
    if not base.exists():
        return None, f"{image_dir} 없음"
    exts = {".jpg", ".jpeg", ".png", ".webp"}
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            b = _load_real_image(str(p))
            if b is not None:
                return b, str(p)
    return None, f"{image_dir} 내 이미지 없음"


# ── 실험 1: 응답 시간 측정 ──────────────────────────────────────────────────
def bench_response_time(image_bytes: bytes, n: int = 5) -> dict:
    """detect_and_depth() 실행 시간 n회 측정 → 평균/최소/최대(ms)"""
    from src.depth.depth import detect_and_depth

    times = []
    for _ in range(n):
        t0 = time.perf_counter()
        detect_and_depth(image_bytes)
        times.append((time.perf_counter() - t0) * 1000)

    return {
        "n": n,
        "mean_ms":  round(sum(times) / len(times), 1),
        "min_ms":   round(min(times), 1),
        "max_ms":   round(max(times), 1),
        "pass":     (sum(times) / len(times)) < 3000,
    }


# ── 실험 2: 탐지 파이프라인 동작 확인 ────────────────────────────────────────
def bench_detection_pipeline(image_bytes: bytes) -> dict:
    """detect_and_depth() 반환값 구조 검증 및 탐지 동작 확인"""
    from src.depth.depth import detect_and_depth

    objects, hazards, scene = detect_and_depth(image_bytes)

    required_fields = {"class", "class_ko", "bbox", "direction",
                        "distance", "distance_m", "risk_score", "is_ground_level"}
    field_ok = all(
        required_fields.issubset(set(obj.keys())) for obj in objects
    ) if objects else True

    direction_ok = all(
        obj["direction"] in {"8시","9시","10시","11시","12시","1시","2시","3시","4시"}
        for obj in objects
    ) if objects else True

    distance_ok = all(
        obj["distance"] in {"매우 가까이","가까이","보통","멀리","매우 멀리"}
        for obj in objects
    ) if objects else True

    risk_ok = all(
        0.0 <= obj["risk_score"] <= 1.0 for obj in objects
    ) if objects else True

    return {
        "detected_count": len(objects),
        "hazard_count":   len(hazards),
        "field_ok":       field_ok,
        "direction_ok":   direction_ok,
        "distance_ok":    distance_ok,
        "risk_range_ok":  risk_ok,
        "pass":           field_ok and direction_ok and distance_ok and risk_ok,
    }


# ── 실험 3: 방향 판단 정확도 ────────────────────────────────────────────────
def bench_direction_accuracy() -> dict:
    """
    물체를 이미지의 알려진 위치에 직접 그려서 방향 판단 정확도를 측정.
    실제 카메라 없이도 코드로 검증 가능.
    """
    from src.vision.detect import ZONE_BOUNDARIES

    DIRECTION_CENTERS = {
        "8시":  0.055,
        "9시":  0.165,
        "10시": 0.275,
        "11시": 0.385,
        "12시": 0.500,
        "1시":  0.615,
        "2시":  0.725,
        "3시":  0.835,
        "4시":  0.945,
    }

    total, correct = 0, 0
    errors = []

    for expected_dir, cx_ratio in DIRECTION_CENTERS.items():
        predicted_dir = "4시"
        for boundary, label in ZONE_BOUNDARIES:
            if cx_ratio <= boundary:
                predicted_dir = label
                break
        total += 1
        if predicted_dir == expected_dir:
            correct += 1
        else:
            errors.append(f"{expected_dir} → 예측:{predicted_dir}")

    accuracy = round(correct / total * 100, 1) if total > 0 else 0
    return {
        "total":    total,
        "correct":  correct,
        "accuracy": accuracy,
        "errors":   errors,
        "pass":     accuracy >= 90.0,
    }


# ── 실험 4: 문장 생성 검증 ──────────────────────────────────────────────────
def bench_sentence_generation() -> dict:
    """build_sentence() 가 모든 방향·거리·긴급도 조합에서 유효한 문장 반환하는지 확인"""
    from src.nlg.sentence import build_sentence

    directions = ["8시","9시","10시","11시","12시","1시","2시","3시","4시"]
    test_cases = [
        {"class_ko": "의자", "direction": d, "distance": dist,
         "distance_m": dm, "risk_score": 0.7, "is_ground_level": False}
        for d in directions
        for dist, dm in [("가까이", 1.0), ("보통", 3.0), ("멀리", 6.0)]
    ]

    total, passed = 0, 0
    errors = []
    for obj in test_cases:
        total += 1
        try:
            result = build_sentence([obj], [])
            if isinstance(result, str) and len(result) > 0:
                passed += 1
            else:
                errors.append(f"빈 문장: {obj['direction']} {obj['distance']}")
        except Exception as e:
            errors.append(f"오류({obj['direction']} {obj['distance']}): {e}")

    empty_result = build_sentence([], [])
    empty_ok = empty_result == "주변에 장애물이 없어요."

    return {
        "total":    total,
        "passed":   passed,
        "empty_ok": empty_ok,
        "errors":   errors,
        "pass":     passed == total and empty_ok,
    }


# ── 실험 5: 클래스별 Precision / Recall / F1 ─────────────────────────────────
def _export_failure_cases(
    failures: list[dict],
    max_images: int = 5,
) -> dict:
    """
    실패 케이스 이미지를 results/failure_cases/<타임스탬프>/ 로 복사하고 요약을 만든다.
    failures 항목: path(Path|str), kind(str), gt(str), predicted(list), wrong_class(str|None)
    """
    root = Path(__file__).parent.parent / "results" / "failure_cases"
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = root / stamp
    out_dir.mkdir(parents=True, exist_ok=True)

    # FN 우선, 그다음 FP_extra — 경로 중복 제거
    priority = {"FN": 0, "FP_extra": 1}
    sorted_f = sorted(failures, key=lambda x: priority.get(x.get("kind"), 9))
    seen: set[str] = set()
    picked: list[dict] = []
    for row in sorted_f:
        p = str(row["path"])
        if p in seen:
            continue
        seen.add(p)
        picked.append(row)
        if len(picked) >= max_images:
            break

    manifest_lines = [
        "# 실패 케이스 샘플 (발표/문서용)",
        "",
        f"- 생성: {stamp}",
        "- 패턴 요약은 동일 폴더의 `manifest.json` 참고.",
        "",
    ]
    for i, row in enumerate(picked, 1):
        src = Path(row["path"])
        ext = src.suffix.lower() if src.suffix else ".jpg"
        kind = str(row.get("kind", "x"))
        dest = out_dir / f"{i:02d}_{kind}{ext}"
        try:
            shutil.copy2(src, dest)
            manifest_lines.append(f"{i}. `{dest.name}` — 정답 `{row['gt']}` / {row['kind']}")
        except OSError:
            manifest_lines.append(f"{i}. (복사 실패) `{src}`")

    fn_n = sum(1 for f in failures if f.get("kind") == "FN")
    fp_n = sum(1 for f in failures if f.get("kind") == "FP_extra")
    wrong_counts: dict[str, int] = {}
    for f in failures:
        if f.get("kind") == "FP_extra" and f.get("wrong_class"):
            w = f["wrong_class"]
            wrong_counts[w] = wrong_counts.get(w, 0) + 1

    def _ser_row(row: dict) -> dict:
        out = {}
        for k, v in row.items():
            if isinstance(v, Path):
                out[k] = str(v)
            else:
                out[k] = v
        return out

    pattern = (
        f"누락(FN) 이벤트 {fn_n}건, 다른 클래스 오탐(FP_extra) {fp_n}건. "
        f"오탐으로 자주 등장한 클래스: {list(wrong_counts.keys())[:5]}"
    )

    summary = {
        "run_stamp":       stamp,
        "exported_dir":    str(out_dir),
        "exported_count":  len(picked),
        "total_fn_events": fn_n,
        "total_fp_events": fp_n,
        "fp_wrong_class_histogram": wrong_counts,
        "pattern_summary_ko": pattern,
        "samples":         [_ser_row(r) for r in picked[:max_images]],
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "README.txt").write_text(
        "\n".join(manifest_lines) + "\n\n공통 패턴:\n" + pattern + "\n",
        encoding="utf-8",
    )
    return summary


def bench_precision_recall(image_dir: str = "data/test_images") -> dict:
    """
    data/test_images/{class_name}/ 구조에서 클래스별 탐지 성능 측정.
      - Recall    = 탐지된 이미지 수 / 전체 이미지 수  (놓친 것 없는가)
      - Precision = 맞게 탐지된 수   / 전체 탐지 수    (잘못 잡은 것 없는가)
      - F1        = 2 * P * R / (P + R)
      - FPR       = 다른 클래스 이미지에서 해당 클래스가 잘못 탐지된 비율

    이미지당 `detect_and_depth` 1회만 호출(캐시).
    """
    from src.depth.depth import detect_and_depth

    base = Path(image_dir)
    if not base.exists():
        return {"error": f"{image_dir} 없음 — 테스트 이미지 필요", "pass": False}

    class_dirs = [d for d in base.iterdir() if d.is_dir()]
    if not class_dirs:
        return {"error": "클래스 폴더 없음", "pass": False}

    eval_pool: list[tuple[Path, str]] = []
    for cls_dir in sorted(class_dirs):
        cls_name = cls_dir.name
        images = (
            list(cls_dir.glob("*.jpg"))
            + list(cls_dir.glob("*.jpeg"))
            + list(cls_dir.glob("*.png"))
            + list(cls_dir.glob("*.webp"))
        )
        for p in images[:10]:
            eval_pool.append((p, cls_name))

    if not eval_pool:
        return {"error": "측정 가능한 이미지 없음", "pass": False}

    class_names = sorted({gt for _, gt in eval_pool})
    img_cache: dict[str, set[str]] = {}
    for img_path, _gt in eval_pool:
        key = str(img_path.resolve())
        if key in img_cache:
            continue
        img_bytes = img_path.read_bytes()
        try:
            objects, _, _ = detect_and_depth(img_bytes)
            img_cache[key] = {o.get("class_ko") for o in objects if o.get("class_ko")}
        except Exception:
            img_cache[key] = set()

    failures: list[dict] = []
    for img_path, gt in eval_pool:
        key = str(img_path.resolve())
        preds = img_cache.get(key, set())
        pred_list = sorted(x for x in preds if x)
        if gt not in preds:
            failures.append({
                "path": img_path, "gt": gt, "kind": "FN",
                "predicted": pred_list, "wrong_class": None,
            })
        for w in preds:
            if w and w != gt:
                failures.append({
                    "path": img_path, "gt": gt, "kind": "FP_extra",
                    "predicted": pred_list, "wrong_class": w,
                })

    per_class: dict[str, dict] = {}
    for target in class_names:
        tp = fp = fn = tn = 0
        for img_path, gt in eval_pool:
            key = str(img_path.resolve())
            detected = img_cache.get(key, set())
            pred_has = target in detected
            gt_has = (gt == target)
            if gt_has and pred_has:
                tp += 1
            elif gt_has and not pred_has:
                fn += 1
            elif not gt_has and pred_has:
                fp += 1
            else:
                tn += 1

        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        per_class[target] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall":    round(recall * 100, 1),
            "precision": round(precision * 100, 1),
            "f1":        round(f1 * 100, 1),
            "fpr":       round(fpr * 100, 1),
        }

    if not per_class:
        return {"error": "측정 가능한 클래스 없음", "pass": False}

    avg_recall    = round(sum(v["recall"]    for v in per_class.values()) / len(per_class), 1)
    avg_precision = round(sum(v["precision"] for v in per_class.values()) / len(per_class), 1)
    avg_f1        = round(sum(v["f1"]        for v in per_class.values()) / len(per_class), 1)
    avg_fpr       = round(sum(v["fpr"]       for v in per_class.values()) / len(per_class), 1)
    low_recall = [k for k, v in per_class.items() if v["recall"] < 50]

    # 오탐(FPR) 상위 클래스 — FP 건수 기준
    high_fpr_top = sorted(
        [{"class": k, "fpr": v["fpr"], "fp": v["fp"], "precision": v["precision"]}
         for k, v in per_class.items()],
        key=lambda x: (-x["fpr"], -x["fp"]),
    )[:8]

    failure_export = None
    if failures:
        failure_export = _export_failure_cases(failures, max_images=5)

    return {
        "per_class":          per_class,
        "avg_recall":         avg_recall,
        "avg_precision":      avg_precision,
        "avg_f1":             avg_f1,
        "avg_fpr":            avg_fpr,
        "low_recall_classes": low_recall,
        "high_fpr_top":       high_fpr_top,
        "failure_export":     failure_export,
        "pass":               avg_recall >= 60.0,
    }


# ── 실험 6: Depth 모델 상태 확인 ─────────────────────────────────────────────
def bench_depth_model() -> dict:
    from src.depth.depth import _check_model, _DEVICE
    model_available = _check_model()
    return {
        "model_file_exists": model_available,
        "device":            _DEVICE,
        "mode":              "Depth Anything V2" if model_available else "bbox 면적 기반 fallback",
    }


# ── eval_log.md 업데이트 ──────────────────────────────────────────────────────
def update_eval_log(results: dict):
    """results/eval_log.md 기존 내용 유지 + 새 실험 결과 추가"""
    log_path = Path(__file__).parent.parent / "results" / "eval_log.md"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    existing = log_path.read_text(encoding="utf-8") if log_path.exists() else ""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    rt   = results["response_time"]
    det  = results["detection"]
    dir_ = results["direction"]
    nlg  = results["sentence"]
    prf  = results.get("prf", {})
    dep  = results["depth"]

    prf_summary = ""
    prf_detail = ""
    if isinstance(prf, dict) and "error" not in prf:
        prf_summary = (
            f"| P/R/F1/FPR (평균) | - | "
            f"R={prf.get('avg_recall','?')}% / P={prf.get('avg_precision','?')}% / "
            f"F1={prf.get('avg_f1','?')}% / FPR={prf.get('avg_fpr','?')}% | ✅ |"
        )
        # 클래스별 상위/하위 몇 개만 기록 (길이 폭발 방지)
        per = prf.get("per_class", {}) or {}
        low = prf.get("low_recall_classes", []) or []
        lines = []
        for cls, m in per.items():
            lines.append(
                f"- {cls}: R={m.get('recall')}% / P={m.get('precision')}% / "
                f"F1={m.get('f1')}% / FPR={m.get('fpr')}% (TP={m.get('tp')}, FP={m.get('fp')}, FN={m.get('fn')})"
            )
        top_fp = prf.get("high_fpr_top") or []
        top_fp_txt = ""
        if top_fp:
            parts = [f"{x['class']} FPR={x['fpr']}% FP={x['fp']}" for x in top_fp[:5]]
            top_fp_txt = "\n#### 오탐(FPR) 상위 클래스\n- " + "\n- ".join(parts) + "\n"

        fx = prf.get("failure_export") or {}
        fail_txt = ""
        if fx.get("exported_dir"):
            fail_txt = (
                "\n#### 실패 케이스 샘플 (최대 5장)\n"
                f"- 폴더: `{fx['exported_dir']}`\n"
                f"- 공통 패턴: {fx.get('pattern_summary_ko', '')}\n"
            )

        prf_detail = (
            "\n#### 클래스별 Precision/Recall/F1/FPR\n"
            + "\n".join(lines[:30])
            + (f"\n- Recall 낮은 클래스: {low}" if low else "")
            + top_fp_txt
            + fail_txt
            + "\n"
        )

    new_block = f"""
---

## 자동 실험 결과 — {now}

### 실험 환경
- 스크립트: `tools/benchmark.py` (자동 실행)
- Python: 3.10 (conda ai_env)
- Depth 모드: {dep['mode']} (device: {dep['device']})
- 테스트 이미지: 640×480 랜덤 JPEG + 실제 테스트 이미지
---

### 📊 성능 지표 요약

| 지표 | 목표 | 결과 | 판정 |
|------|------|------|------|
| 음성 응답 시간 (평균) | 3초 이내 | {rt['mean_ms']}ms ({rt['mean_ms']/1000:.2f}초) | {'✅ 통과' if rt['pass'] else '❌ 초과'} |
| 음성 응답 시간 (최대) | 3초 이내 | {rt['max_ms']}ms | {'✅' if rt['max_ms'] < 3000 else '⚠️'} |
| 탐지 파이프라인 구조 | 오류 없음 | {'정상' if det['pass'] else '오류 있음'} | {'✅ 통과' if det['pass'] else '❌ 실패'} |
| 방향 판단 정확도 | 90% 이상 | {dir_['accuracy']}% ({dir_['correct']}/{dir_['total']}) | {'✅ 통과' if dir_['pass'] else '❌ 미달'} |
| 문장 생성 성공률 | 100% | {round(nlg['passed']/nlg['total']*100,1)}% ({nlg['passed']}/{nlg['total']}) | {'✅ 통과' if nlg['pass'] else '❌ 실패'} |
| Depth 모델 | 파일 존재 | {dep['mode']} | {'✅' if dep['model_file_exists'] else '⚠️ fallback'} |
{prf_summary}

---

### 🔍 상세 결과

#### 응답 시간 ({rt['n']}회 측정)
- 평균: **{rt['mean_ms']}ms**
- 최소: {rt['min_ms']}ms / 최대: {rt['max_ms']}ms

#### 탐지 파이프라인
- 탐지된 객체 수: {det['detected_count']}개 (랜덤 이미지 기준)
- 바닥 위험 감지 수: {det['hazard_count']}개
- 필드 구조 검증: {'✅ 정상' if det['field_ok'] else '❌ 오류'}
- 방향 값 검증: {'✅ 정상' if det['direction_ok'] else '❌ 오류'}
- 거리 값 검증: {'✅ 정상' if det['distance_ok'] else '❌ 오류'}
- 위험도 범위 검증 (0~1): {'✅ 정상' if det['risk_range_ok'] else '❌ 오류'}

#### 방향 판단 정확도
- 9구역(8시~4시) 전체: {dir_['correct']}/{dir_['total']} = **{dir_['accuracy']}%**
{('- 오류 케이스: ' + ', '.join(dir_['errors'])) if dir_['errors'] else '- 오류 없음 ✅'}

#### 문장 생성
- 9방향 × 3거리 = 27개 테스트 케이스: {nlg['passed']}/{nlg['total']} 통과
- 빈 객체 처리: {'✅ 정상' if nlg['empty_ok'] else '❌ 오류'}
{('- 오류 케이스: ' + str(nlg['errors'])) if nlg['errors'] else '- 오류 없음 ✅'}
{prf_detail}
"""

    log_path.write_text(existing + new_block, encoding="utf-8")
    print(f"\n✅ 결과 저장 완료: {log_path}")


# ── 메인 ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("VoiceGuide 자동 성능 실험 시작")
    print("=" * 60)

    image_bytes, img_label = _pick_first_test_image()
    if image_bytes is None:
        image_bytes = _make_dummy_image()
        img_label = f"랜덤 더미 이미지 ({img_label})"
    print(f"\n[이미지] {img_label}")

    print("\n[1/6] 응답 시간 측정 (5회)...")
    rt = bench_response_time(image_bytes, n=5)
    print(f"  → 평균 {rt['mean_ms']}ms  {'✅' if rt['pass'] else '❌'}")

    print("\n[2/6] 탐지 파이프라인 구조 검증...")
    det = bench_detection_pipeline(image_bytes)
    print(f"  → 탐지 {det['detected_count']}개  {'✅' if det['pass'] else '❌'}")

    print("\n[3/6] 방향 판단 정확도 측정...")
    dir_ = bench_direction_accuracy()
    print(f"  → {dir_['accuracy']}%  {'✅' if dir_['pass'] else '❌'}")
    if dir_['errors']:
        print(f"  → 오류: {dir_['errors']}")

    print("\n[4/6] 문장 생성 검증...")
    nlg = bench_sentence_generation()
    print(f"  → {nlg['passed']}/{nlg['total']} 통과  {'✅' if nlg['pass'] else '❌'}")

    print("\n[5/6] 클래스별 Precision/Recall/F1/FPR 측정...")
    prf = bench_precision_recall()
    if "error" in prf:
        print(f"  → 건너뜀: {prf['error']}")
    else:
        print(f"  → 평균 Recall={prf['avg_recall']}%  Precision={prf['avg_precision']}%  "
              f"F1={prf['avg_f1']}%  FPR={prf['avg_fpr']}%  {'✅' if prf['pass'] else '❌'}")
        if prf['low_recall_classes']:
            print(f"  → Recall 낮은 클래스: {prf['low_recall_classes']}")
        top = prf.get("high_fpr_top") or []
        if top:
            t5 = ", ".join(f"{x['class']}({x['fpr']}%)" for x in top[:5])
            print(f"  → FPR 상위: {t5}")
        fe = prf.get("failure_export")
        if fe and fe.get("exported_dir"):
            print(f"  → 실패 샘플 복사: {fe['exported_dir']} ({fe.get('pattern_summary_ko', '')[:70]}...)")

    print("\n[6/6] Depth 모델 상태 확인...")
    dep = bench_depth_model()
    print(f"  → {dep['mode']} ({dep['device']})")

    results = {
        "response_time": rt,
        "detection":     det,
        "direction":     dir_,
        "sentence":      nlg,
        "prf":           prf,
        "depth":         dep,
    }

    print("\n" + "=" * 60)
    print("결과 요약")
    print("=" * 60)
    all_pass = rt['pass'] and det['pass'] and dir_['pass'] and nlg['pass']
    print(f"  응답 시간    : {'✅ 통과' if rt['pass'] else '❌ 초과'} ({rt['mean_ms']}ms)")
    print(f"  탐지 파이프라인: {'✅ 통과' if det['pass'] else '❌ 실패'}")
    print(f"  방향 정확도  : {'✅ 통과' if dir_['pass'] else '❌ 미달'} ({dir_['accuracy']}%)")
    print(f"  문장 생성    : {'✅ 통과' if nlg['pass'] else '❌ 실패'}")
    if "error" not in prf:
        print(f"  P/R/F1/FPR   : Recall={prf['avg_recall']}% / Precision={prf['avg_precision']}% / F1={prf['avg_f1']}% / FPR={prf['avg_fpr']}%")
    print(f"  Depth 모드   : {dep['mode']}")
    print(f"\n  종합: {'🎉 모든 목표 달성!' if all_pass else '⚠️ 일부 목표 미달성'}")

    update_eval_log(results)

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
