# VoiceGuide Demo Video Production Brief

## Goal
Create a 5-10 minute Korean demo video for VoiceGuide that feels like a real product demonstration, not a PPT export.

## Core Message
VoiceGuide recognizes nearby situations on an Android device and guides the user through voice and vibration. Detection happens on-device, while the server records events and provides a live dashboard.

## Hard Rules
- Do not use unrelated stock photos or generic test images.
- Do not include editor/meta phrases such as "removed photos", "cropped screen", "we organized this".
- Do not claim unmeasured Android FPS, mAP50, memory, or real-world safety guarantees.
- Do not imply that the server runs YOLO inference. Real-time detection is Android-side TFLite.
- Do not make a slideshow-looking video. Avoid visible progress bars and large static deck-like pages.
- Use only relevant visuals: real Android app capture, real dashboard capture, and simple motion graphics made for the video.
- Keep all Korean on-screen text large, short, and readable.

## Visual Direction
- Full-screen product demo style.
- Use the real phone capture as the main proof for the Android side.
- Use the dashboard screen recording as the main proof for server/dashboard.
- Use animated system-flow graphics only where no real footage exists.
- Movement should come from camera pans, reveal animations, and live dashboard footage, not fake moving obstacles.

## Story Structure
1. Opening: VoiceGuide name and a clear one-sentence value proposition.
2. Problem: visually impaired walking assistance needs immediate voice/vibration guidance.
3. Android demo: phone capture showing camera, detection state, processing overlay, and voice guidance.
4. System flow: CameraX -> TFLite YOLO -> stabilization -> TTS/vibration -> server JSON -> dashboard.
5. Guidance logic: explain that raw YOLO results are stabilized before speech.
6. Dashboard demo: real dashboard footage, cropped so browser chrome/taskbar are not visible.
7. Verification: show only confirmed values: automated tests, server request latency, NLG latency; mark Android FPS/mAP50/memory as additional measurement items.
8. Closing: summarize detection, guidance, and record/dashboard flow.

## On-Screen Copy Tone
Use direct product language:
- "주변 상황을 인식하고 음성으로 안내합니다"
- "폰에서 바로 탐지하고 안내합니다"
- "탐지 결과를 안정화해 필요한 안내만 전달합니다"
- "탐지 이벤트가 대시보드로 실시간 전송됩니다"
- "확보된 수치와 추가 측정 항목을 분리했습니다"

Avoid:
- "사진을 제거했습니다"
- "크롭했습니다"
- "설명을 크게 정리했습니다"
- "브라우저 화면을 잘라냈습니다"
- Any sentence that sounds like the editor is apologizing inside the final video.
