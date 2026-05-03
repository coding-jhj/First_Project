# [LEGACY] 2026-05-03 삭제된 기능 보존
# 장애물 안내·물건 찾기·물건 확인·질문 모드 외 음성 명령 기능 제거
# 원본 파일: src/api/routes.py, src/nlg/sentence.py

# ════════════════════════════════════════════════════════════════════════
# [routes.py] 삭제된 엔드포인트: POST /vision/clothing
# ════════════════════════════════════════════════════════════════════════

# @router.post("/vision/clothing", dependencies=[Depends(_verify_api_key)])
# async def vision_clothing(
#     image: UploadFile,
#     type:  str = Form("matching"),   # "matching" or "pattern"
# ):
#     """옷 매칭·패턴 분석 — GPT-4o Vision 활용."""
#     from src.vision.gpt_vision import analyze_clothing
#     if type not in ("matching", "pattern"):
#         type = "matching"   # 잘못된 값이면 기본값으로 fallback
#     image_bytes = await image.read()
#     sentence = analyze_clothing(image_bytes, type)
#     return {"sentence": sentence}


# ════════════════════════════════════════════════════════════════════════
# [routes.py] 삭제된 상수 및 함수: _MEAL_CLASSES, _MEAL_DIRECTIONS, _build_meal_sentence()
# ════════════════════════════════════════════════════════════════════════

# _MEAL_CLASSES = {
#     "포크", "칼", "숟가락", "그릇", "컵", "병", "유리잔",
#     "바나나", "사과", "오렌지", "샌드위치", "피자", "도넛",
#     "케이크", "핫도그", "브로콜리", "당근",
# }
# _MEAL_DIRECTIONS = {
#     "바로 앞": "바로 앞에",
#     "왼쪽 앞": "왼쪽 앞에",
#     "오른쪽 앞": "오른쪽 앞에",
#     "왼쪽": "왼쪽에",
#     "오른쪽": "오른쪽에",
# }
#
#
# def _build_meal_sentence(objects: list[dict]) -> str:
#     """식사 모드 전용 문장 — 식기·음식 위치를 친근하게 안내."""
#     from src.nlg.templates import CLOCK_TO_DIRECTION
#     from src.nlg.sentence import _i_ga, _format_dist
#     meal_items = [o for o in objects if o.get("class_ko") in _MEAL_CLASSES]
#     if not meal_items:
#         return "식기나 음식이 보이지 않아요. 카메라를 식탁 쪽으로 향해 주세요."
#     parts = []
#     for obj in meal_items[:3]:
#         name = obj.get("class_ko", "")
#         if not name:
#             continue
#         direction = CLOCK_TO_DIRECTION.get(obj.get("direction", "12시"), "앞")
#         dist = obj.get("distance_m", 1.0)
#         ig = _i_ga(name)
#         loc = _MEAL_DIRECTIONS.get(direction, f"{direction}에")
#         if dist < 0.8:
#             parts.append(f"{loc} {name}{ig} 있어요. 손 뻗으면 닿아요.")
#         else:
#             parts.append(f"{loc} {name}{ig} 있어요.")
#     return " ".join(parts) if parts else "식기나 음식이 보이지 않아요."


# ════════════════════════════════════════════════════════════════════════
# [routes.py] 삭제된 /detect 핸들러 내 식사 도우미 모드 블록
# ════════════════════════════════════════════════════════════════════════

#     # ── 식사 도우미 모드: 식기·음식 위치 집중 안내 ──────────────────────────
#     if mode == "식사":
#         sentence = _build_meal_sentence(objects)
#         return _with_perf({
#             "mode": mode,
#             "sentence":    sentence,
#             "objects":     objects,
#             "hazards":     [],
#             "changes":     [],
#             "alert_mode":  "silent",
#             "depth_source": objects[0].get("depth_source","bbox") if objects else "bbox",
#         }, _t0, request_id, _detect_ms, _tracker_ms)


# ════════════════════════════════════════════════════════════════════════
# [routes.py] 삭제된 /detect 핸들러 내 색상 분석 모드 블록
# ════════════════════════════════════════════════════════════════════════

#     # ── 색상 모드: 가장 큰 물체의 색상 안내 ─────────────────────────────────
#     if mode == "색상":
#         if objects:
#             top = objects[0]  # 위험도 기준 1위 (가장 크거나 가까운 물체)
#             color = top.get("color", "")
#             name  = top.get("class_ko", "물체")
#             sentence = f"{name}는 {color} 계열이에요." if color else f"{name}의 색상을 인식하지 못했어요."
#         else:
#             sentence = "색상을 확인할 물체가 보이지 않아요. 카메라를 물체에 가까이 대주세요."
#         return _with_perf({
#             "mode": mode,
#             "sentence":    sentence,
#             "alert_mode":  "silent",
#             "objects":     objects,
#             "hazards":     hazards,
#             "changes":     [],
#             "depth_source": objects[0].get("depth_source","bbox") if objects else "bbox",
#         }, _t0, request_id, _detect_ms, _tracker_ms)


# ════════════════════════════════════════════════════════════════════════
# [sentence.py] 삭제된 함수: build_navigation_sentence()
# ════════════════════════════════════════════════════════════════════════

# def build_navigation_sentence(
#     label: str,
#     action: str,
#     locations: list[dict] | None = None,
#     wifi_ssid: str = "",
# ) -> str:
#     """
#     개인 네비게이팅 모드의 안내 문장.
#
#     action 종류:
#       "save"       → "편의점을 저장했어요."
#       "found_here" → "편의점이 저장된 위치예요! 도착했어요."
#       "not_found"  → "편의점은 저장된 장소에 없어요."
#       "deleted"    → "편의점을 삭제했어요."
#       "list"       → "저장된 장소는 편의점, 화장실이에요."
#
#     locations: DB에서 조회한 장소 목록 (list 액션에서만 사용)
#     최대 5개만 읽어줌 — TTS가 너무 길어지는 것 방지
#     """
#     if action == "save":
#         label_str = label or "이 장소"
#         return f"{label_str}{_eul_reul(label_str)} 저장했어요."
#     if action == "found_here":
#         return f"{label}{_i_ga(label)} 저장된 위치예요! 도착했어요."
#     if action == "not_found":
#         return f"{label}{_un_neun(label)} 저장된 장소에 없어요. 먼저 그 곳에서 저장해 주세요."
#     if action == "deleted":
#         return f"{label}{_eul_reul(label)} 삭제했어요."
#     if action == "list":
#         if not locations:
#             return "저장된 장소가 없어요. 가고 싶은 곳에서 '여기 저장해줘'라고 말해보세요."
#         names  = [loc["label"] for loc in locations[:5]]  # 최대 5개
#         joined = ", ".join(names)
#         # 5개 초과이면 "외 N곳" 추가
#         suffix = f" 외 {len(locations) - 5}곳" if len(locations) > 5 else ""
#         return f"저장된 장소는 {joined}{suffix}이에요."
#     return "안내를 처리하지 못했어요."
