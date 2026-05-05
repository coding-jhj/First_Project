import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # Windows OpenMP 충돌 방지

from src.vision.detect import detect_objects, TARGET_CLASSES

# detect_objects()가 반환 가능한 유효 값 집합 — 범위 검사에 사용
VALID_DIRECTIONS = {"8시", "9시", "10시", "11시", "12시", "1시", "2시", "3시", "4시"}
VALID_DISTANCES  = {"매우 가까이", "가까이", "보통", "멀리", "매우 멀리"}


def test_target_classes_defined():
    # TARGET_CLASSES에 COCO80 전체 + 파인튜닝 계단 클래스가 모두 포함되어 있는지 확인
    assert "person"       in TARGET_CLASSES
    assert "chair"        in TARGET_CLASSES
    assert "dining table" in TARGET_CLASSES
    assert "backpack"     in TARGET_CLASSES
    assert "suitcase"     in TARGET_CLASSES
    assert "cell phone"   in TARGET_CLASSES
    assert "stairs"       in TARGET_CLASSES   # 파인튜닝 추가 클래스
    # COCO80 전체 포함 확인
    assert "car"          in TARGET_CLASSES
    assert "dog"          in TARGET_CLASSES
    assert "knife"        in TARGET_CLASSES
    assert "banana"       in TARGET_CLASSES
    assert len(TARGET_CLASSES) >= 81   # COCO80 + 계단


def test_detect_objects_returns_tuple(sample_image_bytes):
    # 반환값이 (물체목록, 장면분석) 튜플인지, 최대 3개 물체인지 확인
    result, scene = detect_objects(sample_image_bytes)
    assert isinstance(result, list)   # 탐지 물체 목록
    assert isinstance(scene, dict)    # 장면 분석 결과 (안전경로·군중·신호등 등)
    assert len(result) <= 3           # 위험도 상위 3개만 반환


def test_scene_analysis_keys(sample_image_bytes):
    # scene dict에 Android 앱이 사용하는 4가지 키가 모두 있는지 확인
    _, scene = detect_objects(sample_image_bytes)
    assert "safe_direction" in scene  # 안전 경로 제안 문자열
    assert "crowd_warning"  in scene  # 군중 밀집 경고
    assert "danger_warning" in scene  # 위험 물체(칼·가위) 경고
    assert "person_count"   in scene  # 감지된 사람 수 (군중 판단 기준)


def test_detect_objects_fields(sample_image_bytes):
    # 각 탐지 물체 dict에 필수 필드가 모두 있고 값 범위가 올바른지 확인
    result, _ = detect_objects(sample_image_bytes)
    for obj in result:
        assert "class"           in obj  # 영어 클래스명 (COCO 표준)
        assert "class_ko"        in obj  # 한국어 클래스명 (TTS 안내용)
        assert "bbox"            in obj  # [x1,y1,x2,y2] 픽셀 좌표
        assert "obb_xyxyxyxy"    in obj  # OBB 4점 픽셀 좌표
        assert "obb_norm_xyxyxyxy" in obj  # Android overlay용 정규화 OBB 4점 좌표
        assert "direction"       in obj  # 시계 방향 (8시~4시)
        assert "distance"        in obj  # 거리 레이블 ("가까이" 등)
        assert "distance_m"      in obj  # 미터 단위 추정 거리
        assert "risk_score"      in obj  # 0.0~1.0 위험도 점수
        assert "is_ground_level" in obj  # 바닥 장애물 여부
        assert "is_vehicle"      in obj  # 이동 차량 여부 (최고 위험)
        assert "is_animal"       in obj  # 동물 여부 (돌발 행동 위험)
        assert "is_dangerous"    in obj  # 날카로운 물체 여부
        assert obj["direction"]  in VALID_DIRECTIONS   # 9구역 시계 방향 중 하나
        assert obj["distance"]   in VALID_DISTANCES    # 5단계 거리 레이블 중 하나
        assert 0.0 <= obj["risk_score"] <= 1.0         # 위험도는 0~1 범위
        assert obj["distance_m"] >= 0.1                # 거리는 최소 10cm 이상
        assert isinstance(obj["is_ground_level"], bool)
        assert len(obj["obb_xyxyxyxy"]) == 4
        assert len(obj["obb_norm_xyxyxyxy"]) == 4
        assert all(len(point) == 2 for point in obj["obb_norm_xyxyxyxy"])
