package com.voiceguide

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import java.nio.FloatBuffer

/**
 * YOLO 온디바이스 추론기
 *
 * 서버 없이 폰 단독으로 물체를 탐지합니다.
 * PyTorch로 학습한 YOLO 모델을 ONNX 포맷으로 변환해서 Android에서 실행.
 *
 * ONNX란?
 *   Open Neural Network Exchange — 딥러닝 모델의 범용 저장 포맷.
 *   PyTorch/TensorFlow 등 어떤 프레임워크로 만든 모델이든
 *   ONNX로 변환하면 Android·iOS·PC 어디서든 실행 가능.
 *
 * 서버 연동과 온디바이스 추론:
 *   서버 연동: 온디바이스 탐지 JSON → 서버 저장/대시보드 → 폰
 *   온디바이스: 이미지 → 폰 내 ONNX 추론 → 결과 (서버 불필요)
 */

/**
 * YOLO 탐지 결과 한 건을 담는 데이터 클래스.
 * data class = equals/hashCode/toString 자동 생성 + copy() 사용 가능.
 */
data class Detection(
    val classKo: String,     // 한국어 클래스명 ("의자", "자동차" 등)
    val confidence: Float,   // 확신도 0.0~1.0
    val cx: Float,           // 바운딩 박스 중심 X (이미지 너비 기준 0.0~1.0)
    val cy: Float,           // 바운딩 박스 중심 Y (이미지 높이 기준 0.0~1.0)
    val w: Float,            // 바운딩 박스 너비 (0.0~1.0)
    val h: Float,            // 바운딩 박스 높이 (0.0~1.0)
    val isFound: Boolean = false,  // 찾기 모드에서 발견된 대상이면 true (흰색 박스)
    val trackId: Int = 0,
    val riskScore: Float = 0f,
    val vibrationPattern: String = "NONE",
    val distanceM: Float = 0f
)

class YoloDetector(context: Context) {

    private val env = OrtEnvironment.getEnvironment()  // ONNX 실행 환경 (앱당 1개)
    private val session: OrtSession                    // 모델 세션 (추론 단위)
    private val inputName: String
    val modelName: String
    private val inputSize   = 640       // YOLO 입력 해상도 (640×640)
    private val confThreshold = 0.40f   // 오탐 방지 — 서버(0.50)에 근접한 임계값
    private val iouThreshold  = 0.45f   // NMS IoU 임계값: 겹치는 박스 제거 기준
    private var outputShapeLogged = false

    init {
        // assets 폴더에서 ONNX 모델 로드
        // 우선순위: yolo11n.onnx (10MB, 온디바이스 기본) → yolo11m.onnx (80MB, 고정밀)
        modelName = listOf("yolo11n.onnx", "yolo11m.onnx").first { name ->
            try {
                context.assets.open(name).close()
                true
            } catch (_: Exception) {
                false
            }
        }
        val bytes = context.assets.open(modelName).readBytes()
        // CPU 코어 수: 추론 전용 스레드 1개이므로 intra-op 스레드만 활용
        val cores = Runtime.getRuntime().availableProcessors().coerceIn(2, 4)
        fun cpuOptions() = OrtSession.SessionOptions().apply {
            setIntraOpNumThreads(cores)
            setInterOpNumThreads(1)
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        }
        // NNAPI는 Android 10(API 29) 이상 + 모델 호환성 두 조건 모두 충족해야 안정적
        val canTryNnapi = android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q
        session = if (canTryNnapi) {
            try {
                val nnapiOpts = cpuOptions().apply { addNnapi() }
                env.createSession(bytes, nnapiOpts).also {
                    android.util.Log.d("VG_PERF", "NNAPI + CPU $cores 스레드 — $modelName")
                }
            } catch (e: Exception) {
                android.util.Log.w("VG_PERF",
                    "NNAPI 세션 실패 → CPU fallback — $modelName: ${e.message}")
                env.createSession(bytes, cpuOptions()).also {
                    android.util.Log.d("VG_PERF", "CPU $cores 스레드 추론 — $modelName")
                }
            }
        } else {
            env.createSession(bytes, cpuOptions()).also {
                android.util.Log.d("VG_PERF", "CPU $cores 스레드 추론 (API<29) — $modelName")
            }
        }
        inputName = session.inputNames.iterator().next()
    }

    fun detect(bitmap: Bitmap): List<Detection> {
        val origW = bitmap.width
        val origH = bitmap.height

        // 비율을 유지하며 640x640에 맞추고 나머지는 검정 패딩 (letterboxing)
        val scale  = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
        val scaledW = (origW * scale + 0.5f).toInt()
        val scaledH = (origH * scale + 0.5f).toInt()
        val padX   = (inputSize - scaledW) / 2
        val padY   = (inputSize - scaledH) / 2

        val letterboxed = Bitmap.createBitmap(inputSize, inputSize, Bitmap.Config.ARGB_8888)
        val lbCanvas = android.graphics.Canvas(letterboxed)
        lbCanvas.drawARGB(255, 0, 0, 0)
        val scaled = Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)
        lbCanvas.drawBitmap(scaled, padX.toFloat(), padY.toFloat(), null)
        scaled.recycle()

        val inputBuffer = bitmapToNCHW(letterboxed)
        letterboxed.recycle()

        // 텐서 shape: [1, 3, 640, 640] = [batch, RGB채널, H, W]
        val tensor = OnnxTensor.createTensor(
            env, inputBuffer, longArrayOf(1, 3, inputSize.toLong(), inputSize.toLong())
        )

        try {
            // 추론 실행
            val output = session.run(mapOf(inputName to tensor))
            try {
                val outputTensor = output[0] as ai.onnxruntime.OnnxTensor

                // YOLO 출력 shape: [1, numFeatures, 8400]
                // numFeatures = 4(bbox) + 클래스 수
                // 8400 = 3가지 스케일 × 각 스케일의 격자 수 합 (20×20 + 40×40 + 80×80)
                val shape       = outputTensor.info.shape
                val numFeatures = shape[1].toInt()  // 84(COCO80) 또는 85(indoor81)
                val numDet      = shape[2].toInt()  // 8400
                val flatBuf     = outputTensor.floatBuffer  // 1D float 배열
                if (!outputShapeLogged) {
                    outputShapeLogged = true
                    android.util.Log.d(
                        "VG_PERF",
                        "YOLO output model=$modelName shape=${shape.joinToString(prefix = "[", postfix = "]")}"
                    )
                }

                return postProcess(flatBuf, numFeatures, numDet, padX, padY, scaledW, scaledH)
            } finally {
                output.close()
            }
        } finally {
            tensor.close()
        }
    }

    /**
     * Android Bitmap → ONNX NCHW Float 텐서 변환
     *
     * NCHW = [N배치, C채널, H높이, W너비]
     * YOLO는 픽셀값을 0~255가 아닌 0.0~1.0으로 정규화해서 받음
     * 채널 순서: RGB (Android Bitmap은 ARGB이므로 A 제거 필요)
     */
    private fun bitmapToNCHW(bitmap: Bitmap): FloatBuffer {
        val pixels = IntArray(inputSize * inputSize)
        // getPixels: 픽셀을 ARGB Int 배열로 읽음
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)

        val planeSize = inputSize * inputSize
        val data = FloatArray(3 * planeSize)
        for (i in pixels.indices) {
            // ARGB Int에서 각 채널 추출 (비트 시프트 + AND 마스크)
            data[i] = ((pixels[i] shr 16) and 0xFF) / 255f                 // R
            data[planeSize + i] = ((pixels[i] shr 8) and 0xFF) / 255f      // G
            data[planeSize * 2 + i] = (pixels[i] and 0xFF) / 255f          // B
        }

        return FloatBuffer.wrap(data)
    }

    /**
     * YOLO 출력 후처리: 박스 필터링 + NMS
     *
     * YOLO 출력 레이아웃:
     *   buf[feature_idx * numDet + det_idx]
     *   feature 0~3: bbox (cx, cy, w, h) — letterbox 640px 단위
     *   feature 4~(4+numClasses-1): 각 클래스의 confidence score
     */
    private fun postProcess(
        buf: java.nio.FloatBuffer,
        numFeatures: Int, numDet: Int,
        padX: Int, padY: Int, scaledW: Int, scaledH: Int
    ): List<Detection> {
        val numClasses = numFeatures - 4
        if (numClasses <= 0) {
            android.util.Log.w("VG_PERF", "Invalid YOLO output shape model=$modelName features=$numFeatures")
            return emptyList()
        }
        val candidates = mutableListOf<Detection>()

        for (i in 0 until numDet) {
            var maxScore = confThreshold
            var maxClass = -1
            for (c in 0 until numClasses) {
                val s = buf.get((4 + c) * numDet + i)
                if (s > maxScore) { maxScore = s; maxClass = c }
            }
            if (maxClass < 0) continue
            val name = COCO_KO[maxClass] ?: continue

            // YOLO 출력 좌표는 letterbox된 640x640 공간의 픽셀값
            // → 패딩 제거 후 원본 이미지 [0,1] 비율로 변환
            val cxPx = buf.get(0 * numDet + i)
            val cyPx = buf.get(1 * numDet + i)
            val wPx  = buf.get(2 * numDet + i)
            val hPx  = buf.get(3 * numDet + i)

            val cx = (cxPx - padX) / scaledW
            val cy = (cyPx - padY) / scaledH
            val w  = wPx / scaledW
            val h  = hPx / scaledH

            // 패딩 영역(검정 바깥)에 중심이 있으면 무시
            if (cx < 0f || cx > 1f || cy < 0f || cy > 1f) continue

            candidates.add(Detection(
                classKo    = name,
                confidence = maxScore,
                cx = cx, cy = cy, w = w, h = h
            ))
        }

        return nms(candidates.sortedByDescending { it.confidence }).take(8)
    }

    /**
     * NMS (Non-Maximum Suppression) — 겹치는 박스 제거
     *
     * 같은 물체를 여러 박스가 탐지하면 가장 확신도 높은 것만 남기고 제거.
     * iouThreshold: IoU가 이 값 이상이면 "같은 물체"로 판단해서 제거
     * IoU(Intersection over Union) = 두 박스의 겹치는 면적 / 합친 면적
     */
    private fun nms(sorted: List<Detection>): List<Detection> {
        val keep = mutableListOf<Detection>()
        val skip = BooleanArray(sorted.size)  // true이면 이미 제거된 박스

        for (i in sorted.indices) {
            if (skip[i]) continue
            keep.add(sorted[i])  // 살아남은 박스
            // i번 박스와 겹치는 모든 후순위 박스 제거
            for (j in i + 1 until sorted.size) {
                if (!skip[j] && iou(sorted[i], sorted[j]) > iouThreshold) skip[j] = true
            }
        }
        return keep
    }

    /**
     * 두 Detection 박스의 IoU(겹침 비율) 계산.
     * 0.0 = 전혀 안 겹침, 1.0 = 완전히 같은 박스
     */
    private fun iou(a: Detection, b: Detection): Float {
        // 각 박스의 좌상단/우하단 좌표 계산 (cx,cy,w,h → x1,y1,x2,y2)
        val ax1 = a.cx - a.w / 2; val ay1 = a.cy - a.h / 2
        val ax2 = a.cx + a.w / 2; val ay2 = a.cy + a.h / 2
        val bx1 = b.cx - b.w / 2; val by1 = b.cy - b.h / 2
        val bx2 = b.cx + b.w / 2; val by2 = b.cy + b.h / 2

        // 교집합 너비/높이 (음수면 겹침 없음 → 0으로 clamp)
        val iw = maxOf(0f, minOf(ax2, bx2) - maxOf(ax1, bx1))
        val ih = maxOf(0f, minOf(ay2, by2) - maxOf(ay1, by1))
        val inter = iw * ih                        // 교집합 면적
        val union = a.w * a.h + b.w * b.h - inter // 합집합 면적

        return if (union > 0) inter / union else 0f
    }

    fun close() {
        session.close()
        env.close()
    }
}
