# 제거된 기능 목록

> 제거 일자: 2026-05-03  
> 유지 기능: 장애물 안내, 물건 찾기, 물건 확인, 질문 모드

## 제거된 음성 명령 기능

| 기능 | STT 키워드 | 제거된 코드 위치 |
|------|-----------|----------------|
| 텍스트 인식(OCR) | 글자 읽어줘, 간판 읽어줘 | MainActivity.kt `captureForOcr()` |
| 바코드 인식 | 바코드, 상품 뭐야 | MainActivity.kt `captureForBarcode()` |
| 색상 분석 | 무슨 색이야, 색깔 알려줘 | routes.py 색상 모드 블록 |
| 밝기 감지 | 얼마나 밝아, 어두워 | MainActivity.kt 밝기 센서 핸들링 |
| 식사 도우미 | 밥 먹을게, 식사 모드 | routes.py `_build_meal_sentence()` |
| 옷 매칭 조언 | 어울려, 코디 | routes.py `/vision/clothing`, MainActivity.kt `captureForClothingAdvice()` |
| 옷 패턴 분석 | 패턴, 무늬 | routes.py `/vision/clothing`, MainActivity.kt `captureForClothingAdvice()` |
| 지폐 인식 | 이 돈 얼마야, 몇 원 | MainActivity.kt `captureForCurrency()` |
| 위치 저장 | 여기 저장해줘, 기억해줘 | MainActivity.kt 저장 케이스, sentence.py `build_navigation_sentence()` |
| 위치 목록 | 저장된 곳, 장소 목록 | MainActivity.kt 위치목록 케이스, sentence.py `build_navigation_sentence()` |
| 하차 알림 | 도착하면 알려줘 | MainActivity.kt `startGpsTracking()` |
| 약 복용 알림 | 약 먹어야 해, 약 알림 설정 | MainActivity.kt `setMedicationAlarm()` |
| 다시 읽기 | 다시, 못 들었어 | MainActivity.kt 다시읽기 케이스 |
| 볼륨 조절 | 소리 크게, 소리 작게 | MainActivity.kt 볼륨업/다운 케이스 |
| 일시정지/재시작 | 잠깐, 멈춰 / 다시 시작 | MainActivity.kt 중지/재시작 케이스 |
| 긴급 SOS | 살려줘, 119 | MainActivity.kt `triggerSOS()` |

## 보존 파일
- `legacy/android_removed_features.kt` — Android 삭제 코드 원본
- `legacy/server_removed_features.py` — 서버 삭제 코드 원본

## 복구 방법
각 legacy 파일에서 해당 코드를 복사해 원본 파일에 붙여넣고,
VoiceGuideConstants.kt STT_KEYWORDS에 해당 키워드를 다시 추가하면 복구됩니다.
