"""
test_heatmap_runner.py
dashboard.html _haversineM + HEATMAP_RADIUS_M Python 재현 단위 테스트
test_heatmap.js 와 완전히 동일한 4개 시나리오를 검증한다.

실행: python tools/test_heatmap_runner.py

[좌표 선정 근거]
simulator.py ROUTE 실측 결과, 출발 "아파트 입구"(37.653404, 127.043607)에서
위험지점("상가옆2" 37.652854, 127.045359)까지 직선 165.9 m 로
이미 200 m 이내다. TC-1 에서는 "200 m 초과" 조건을 검증하기 위해
위험지점에서 정서(正西) 250 m 인 가상 원거리 지점을 사용한다.
"""

import math
import sys
import io

# Windows 콘솔 한글 출력 보장
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ----------------------------------------------------------
#  dashboard.html 원본 로직 (JS -> Python 직역, 알고리즘 동일)
# ----------------------------------------------------------
HEATMAP_RADIUS_M = 200

def _haversineM(lat1, lng1, lat2, lng2):
    R = 6_371_000
    f = math.pi / 180
    phi1, phi2 = lat1 * f, lat2 * f
    dphi = (lat2 - lat1) * f
    dlam = (lng2 - lng1) * f
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ----------------------------------------------------------
#  테스트 유틸
# ----------------------------------------------------------
passed = 0
failed = 0

def assert_test(condition, label, extra=""):
    global passed, failed
    tag = "PASS" if condition else "FAIL"
    suffix = f"  ({extra})" if extra else ""
    print(f"  {tag}  {label}{suffix}")
    if condition:
        passed += 1
    else:
        failed += 1

def lerp(lat1, lng1, lat2, lng2, t):
    return lat1 + (lat2 - lat1) * t, lng1 + (lng2 - lng1) * t

# ----------------------------------------------------------
#  기준 좌표
# ----------------------------------------------------------
DANGER_LAT, DANGER_LNG = 37.652854, 127.045359   # ROUTE "상가옆2" 위험지점

# 위험지점 정서(正西) 250 m: 경도 차 = 250 / (111195 * cos(lat))
FAR_LAT = DANGER_LAT
FAR_LNG = DANGER_LNG - 250 / (111_195 * math.cos(DANGER_LAT * math.pi / 180))

print("=" * 60)
print(" dashboard.html 히트맵 근접 로직 단위 테스트")
print("=" * 60)
print(f"  위험 지점   : ({DANGER_LAT}, {DANGER_LNG})  '상가옆2'")
print(f"  원거리 기점 : ({FAR_LAT}, {FAR_LNG:.6f})  위험지점 정서 250 m")
print(f"  HEATMAP_RADIUS_M: {HEATMAP_RADIUS_M} m")
print()

# ----------------------------------------------------------
#  TC-1: 원거리 지점(250 m) -> 거리 > 200 m  (히트맵 숨김)
# ----------------------------------------------------------
print("-- TC-1: 원거리(250 m) 지점에서는 히트맵이 보이지 않아야 한다 --")
d1 = _haversineM(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG)
print(f"  거리: {d1:.1f} m")
assert_test(
    d1 > HEATMAP_RADIUS_M,
    f"원거리({d1:.1f} m) > HEATMAP_RADIUS_M({HEATMAP_RADIUS_M} m)",
    "히트맵 숨김 조건 충족"
)
print()

# ----------------------------------------------------------
#  TC-2: 원거리 지점에서 위험지점 직전 100 m 위치 -> 거리 <= 200 m (히트맵 표시)
# ----------------------------------------------------------
print("-- TC-2: 위험지점 100 m 앞에서는 히트맵이 보여야 한다 --")
total_dist = _haversineM(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG)
t2 = max(0.0, 1 - 100 / total_dist)
p2_lat, p2_lng = lerp(FAR_LAT, FAR_LNG, DANGER_LAT, DANGER_LNG, t2)
d2 = _haversineM(p2_lat, p2_lng, DANGER_LAT, DANGER_LNG)
print(f"  보간 위치: ({p2_lat:.6f}, {p2_lng:.6f})  t={t2:.4f}")
print(f"  거리: {d2:.1f} m")
assert_test(
    d2 <= HEATMAP_RADIUS_M,
    f"직전 100 m 지점({d2:.1f} m) <= HEATMAP_RADIUS_M({HEATMAP_RADIUS_M} m)",
    "히트맵 표시 조건 충족"
)
print()

# ----------------------------------------------------------
#  TC-3: 위험지점 통과 후 250 m -> 거리 > 200 m (히트맵 사라짐)
#  방향: 다음 ROUTE 포인트 "큰길1" (37.652790, 127.045507)
# ----------------------------------------------------------
print("-- TC-3: 위험지점 250 m 통과 후 히트맵이 사라져야 한다 --")
NEXT_LAT, NEXT_LNG = 37.652790, 127.045507
d_lat = NEXT_LAT - DANGER_LAT
d_lng = NEXT_LNG - DANGER_LNG
seg_len = math.sqrt(d_lat**2 + d_lng**2)
scale250 = 250 / 111_195
p3_lat = DANGER_LAT + (d_lat / seg_len) * scale250
p3_lng = DANGER_LNG + (d_lng / seg_len) * scale250
d3 = _haversineM(p3_lat, p3_lng, DANGER_LAT, DANGER_LNG)
print(f"  통과 250 m 위치: ({p3_lat:.6f}, {p3_lng:.6f})")
print(f"  거리: {d3:.1f} m")
assert_test(
    d3 > HEATMAP_RADIUS_M,
    f"통과 250 m 지점({d3:.1f} m) > HEATMAP_RADIUS_M({HEATMAP_RADIUS_M} m)",
    "히트맵 숨김 조건 충족"
)
print()

# ----------------------------------------------------------
#  TC-4: 기본 정확도 - 서울 위도에서 위도 0.001 deg ~= 111 m
#  이론값: 0.001 * 111195 = 111.195 m
# ----------------------------------------------------------
print("-- TC-4: _haversineM 기본 정확도  위도 0.001 deg ~= 111 m --")
base_lat, base_lng = 37.650000, 127.045000
d4 = _haversineM(base_lat, base_lng, base_lat + 0.001, base_lng)
expected = 111.195
tolerance = 2.0
print(f"  측정값: {d4:.3f} m  (이론값: ~{expected} m, 허용 +-{tolerance} m)")
assert_test(
    abs(d4 - expected) < tolerance,
    f"|{d4:.3f} - {expected}| = {abs(d4 - expected):.3f} m < {tolerance} m",
    "Haversine 정확도 OK"
)
print()

# ----------------------------------------------------------
#  결과 요약
# ----------------------------------------------------------
total = passed + failed
print("=" * 60)
fail_note = f"  ({failed}개 실패)" if failed > 0 else "  (전체 통과)"
print(f" 결과: {passed}/{total} 통과{fail_note}")
print("=" * 60)

sys.exit(1 if failed > 0 else 0)
