package com.voiceguide

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Rect
import android.os.SystemClock
import android.util.Log
import java.nio.FloatBuffer
import java.util.ArrayDeque

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
 * 서버 모드와 온디바이스 모드 비교:
 *   서버 모드: 이미지 → WiFi → PC → YOLO + Depth V2 → 결과 → 폰
 *   온디바이스: 이미지 → 폰 내 ONNX 추론 → 결과 (서버 불필요)
 */

/**
 * YOLO 탐지 결과 한 건을 담는 데이터 클래스.
 * data class = equals/hashCode/toString 자동 생성 + copy() 사용 가능.
 */
data class Detection(
    val classKo: String,     // 한국어 클래스명 ("의자", "자동차" 등)
    val confidence: Float,   // 확신도 0.0~1.0 (0.5 이상만 사용)
    val cx: Float,           // 바운딩 박스 중심 X (이미지 너비 기준 0.0~1.0)
    val cy: Float,           // 바운딩 박스 중심 Y (이미지 높이 기준 0.0~1.0)
    val w: Float,            // 바운딩 박스 너비 (0.0~1.0)
    val h: Float             // 바운딩 박스 높이 (0.0~1.0)
)

data class YoloTiming(
    val preprocessMs: Long = 0,
    val yoloMs: Long = 0,
    val postprocessMs: Long = 0,
    val totalMs: Long = 0,
    val rawCandidates: Int = 0,
    val keptCount: Int = 0
)

data class YoloInput(
    val buffer: FloatBuffer,
    val preprocessMs: Long,
    val totalStartNs: Long
)

data class YoloRawOutput(
    val values: FloatArray,
    val numFeatures: Int,
    val numDet: Int,
    val valueCount: Int,
    val preprocessMs: Long,
    val yoloMs: Long,
    val totalStartNs: Long
)

data class YoloDetectionResult(
    val detections: List<Detection>,
    val timing: YoloTiming
)

class YoloDetector(context: Context) {

    private val env = OrtEnvironment.getEnvironment()  // ONNX 실행 환경 (앱당 1개)
    private val session: OrtSession                    // 모델 세션 (추론 단위)
    val providerName: String
    private val inputSize   = 320       // YOLO 입력 해상도 (320×320, FPS 우선)
    private val confThreshold = 0.50f   // 서버(detect.py)의 CONF_THRESHOLD와 동일하게 맞춤
    private val iouThreshold  = 0.45f   // NMS IoU 임계값: 겹치는 박스 제거 기준
    private val inputArea = inputSize * inputSize
    private val inputPixels = IntArray(inputArea)
    private val inputTensorSize = 3 * inputArea
    private val inputPoolLock = Any()
    private val inputPool = ArrayDeque<FloatBuffer>()
    private val outputPoolLock = Any()
    private val outputPool = ArrayDeque<FloatArray>()
    private val resizedBitmap = Bitmap.createBitmap(inputSize, inputSize, Bitmap.Config.ARGB_8888)
    private val resizeCanvas = Canvas(resizedBitmap)
    private val resizePaint = Paint().apply { isFilterBitmap = false }
    private val resizeDst = Rect(0, 0, inputSize, inputSize)
    var lastTiming = YoloTiming()
        private set

    init {
        // assets 폴더에서 ONNX 모델 로드
        // yolo11m.onnx 우선, 없으면 yolo11n.onnx (더 작은 모델) fallback
        val modelName = try {
            context.assets.open("yolo11m.onnx").close()
            "yolo11m.onnx"  // m 모델: 더 정확 (38MB)
        } catch (_: Exception) {
            "yolo11n.onnx"  // n 모델: 더 빠름 (5.4MB), 오탐 많음
        }
        val bytes = context.assets.open(modelName).readBytes()
        val cpuThreads = Runtime.getRuntime().availableProcessors().coerceIn(1, 4)
        var activeProvider = "CPU"
        // SessionOptions: 현재 YOLO ONNX 모델은 XNNPACK 일부 fallback에서 느려질 수 있어 CPU 멀티스레드 우선
        val options = OrtSession.SessionOptions().apply {
            setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            setInterOpNumThreads(1)
            setIntraOpNumThreads(cpuThreads)
            if (USE_XNNPACK) {
                try {
                    setIntraOpNumThreads(1)
                    addXnnpack(mapOf("intra_op_num_threads" to cpuThreads.toString()))
                    activeProvider = "XNNPACK"
                } catch (e: Exception) {
                    setIntraOpNumThreads(cpuThreads)
                    Log.w(TAG, "XNNPACK 사용 실패, CPU 실행으로 fallback: ${e.message}")
                }
            }
        }
        providerName = activeProvider
        session = env.createSession(bytes, options)
        Log.i(TAG, "YOLO ONNX provider=$providerName, threads=$cpuThreads, model=$modelName")
    }

    fun preprocess(bitmap: Bitmap): YoloInput {
        val totalStart = SystemClock.elapsedRealtimeNanos()
        val preprocessStart = SystemClock.elapsedRealtimeNanos()
        // 1. 이미지를 모델 입력 크기로 리사이즈 (YOLO 고정 입력 해상도)
        val resizeSrc = Rect(0, 0, bitmap.width, bitmap.height)
        resizeCanvas.drawBitmap(bitmap, resizeSrc, resizeDst, resizePaint)
        // 2. Android Bitmap → ONNX Float 텐서 포맷으로 변환
        val prepared = acquireInputData()
        bitmapToNCHW(resizedBitmap, prepared)
        return YoloInput(
            buffer = prepared,
            preprocessMs = nanosToMs(SystemClock.elapsedRealtimeNanos() - preprocessStart),
            totalStartNs = totalStart
        )
    }

    fun runInference(input: YoloInput): YoloRawOutput {
        // 3. ONNX 세션에 입력 이름 확인 (YOLO11은 보통 "images")
        val inputName = session.inputNames.iterator().next()
        // 텐서 shape: [1, 3, inputSize, inputSize] = [batch, RGB채널, H, W]
        input.buffer.rewind()
        val tensor = OnnxTensor.createTensor(
            env, input.buffer, longArrayOf(1, 3, inputSize.toLong(), inputSize.toLong())
        )

        // 4. 추론 실행
        try {
            val yoloStart = SystemClock.elapsedRealtimeNanos()
            val output = session.run(mapOf(inputName to tensor))
            val yoloMs = nanosToMs(SystemClock.elapsedRealtimeNanos() - yoloStart)
            try {
                val outputTensor = output[0] as ai.onnxruntime.OnnxTensor

                // YOLO 출력 shape: [1, numFeatures, numDet]
                // numFeatures = 4(bbox) + 클래스 수
                // numDet = 320 입력 기준 2100, 640 입력 기준 8400
                val shape       = outputTensor.info.shape
                val numFeatures = shape[1].toInt()  // 84(COCO80) 또는 85(indoor81)
                val numDet      = shape[2].toInt()  // 8400
                val flatBuf     = outputTensor.floatBuffer  // 1D float 배열
                val valueCount  = numFeatures * numDet
                val values      = acquireOutputData(valueCount)
                flatBuf.get(values, 0, valueCount)

                return YoloRawOutput(
                    values = values,
                    numFeatures = numFeatures,
                    numDet = numDet,
                    valueCount = valueCount,
                    preprocessMs = input.preprocessMs,
                    yoloMs = yoloMs,
                    totalStartNs = input.totalStartNs
                )
            } finally {
                output.close()
            }
        } finally {
            tensor.close()
            releaseInput(input)
        }
    }

    fun postprocess(raw: YoloRawOutput): YoloDetectionResult {
        val postStart = SystemClock.elapsedRealtimeNanos()
        try {
            val result = postProcess(raw.values, raw.numFeatures, raw.numDet)
            val postMs = nanosToMs(SystemClock.elapsedRealtimeNanos() - postStart)
            val timing = YoloTiming(
                preprocessMs = raw.preprocessMs,
                yoloMs = raw.yoloMs,
                postprocessMs = postMs,
                totalMs = nanosToMs(SystemClock.elapsedRealtimeNanos() - raw.totalStartNs),
                rawCandidates = result.rawCandidates,
                keptCount = result.detections.size
            )
            lastTiming = timing
            return YoloDetectionResult(result.detections, timing)
        } finally {
            releaseOutput(raw)
        }
    }

    fun detect(bitmap: Bitmap): List<Detection> {
        val result = postprocess(runInference(preprocess(bitmap)))
        return result.detections
    }

    /**
     * Android Bitmap → ONNX NCHW Float 텐서 변환
     *
     * NCHW = [N배치, C채널, H높이, W너비]
     * YOLO는 픽셀값을 0~255가 아닌 0.0~1.0으로 정규화해서 받음
     * 채널 순서: RGB (Android Bitmap은 ARGB이므로 A 제거 필요)
     *
     * 메모리 배치: R채널 전체 → G채널 전체 → B채널 전체
     * (인터리브 방식 RGBRGBㆍㆍㆍ이 아님)
     */
    private fun bitmapToNCHW(bitmap: Bitmap, target: FloatBuffer) {
        // getPixels: 픽셀을 ARGB Int 배열로 읽음
        bitmap.getPixels(inputPixels, 0, inputSize, 0, 0, inputSize, inputSize)

        for (i in inputPixels.indices) {
            // ARGB Int에서 각 채널 추출 (비트 시프트 + AND 마스크)
            val pixel = inputPixels[i]
            target.put(i, ((pixel shr 16) and 0xFF) / 255f)
            target.put(inputArea + i, ((pixel shr 8) and 0xFF) / 255f)
            target.put(inputArea * 2 + i, (pixel and 0xFF) / 255f)
        }
    }

    private fun acquireInputData(): FloatBuffer {
        synchronized(inputPoolLock) {
            if (!inputPool.isEmpty()) return inputPool.removeFirst().also { it.clear() }
        }
        return FloatBuffer.allocate(inputTensorSize)
    }

    fun releaseInput(input: YoloInput) {
        synchronized(inputPoolLock) {
            if (inputPool.size < MAX_INPUT_POOL_SIZE) inputPool.addLast(input.buffer)
        }
    }

    private fun acquireOutputData(minSize: Int): FloatArray {
        synchronized(outputPoolLock) {
            while (!outputPool.isEmpty()) {
                val pooled = outputPool.removeFirst()
                if (pooled.size >= minSize) return pooled
            }
        }
        return FloatArray(minSize)
    }

    private fun releaseOutput(raw: YoloRawOutput) {
        synchronized(outputPoolLock) {
            if (outputPool.size < MAX_OUTPUT_POOL_SIZE) outputPool.addLast(raw.values)
        }
    }

    private data class PostProcessResult(
        val detections: List<Detection>,
        val rawCandidates: Int
    )

    /**
     * YOLO 출력 후처리: 박스 필터링 + NMS
     *
     * YOLO 출력 레이아웃 (NCHW가 아닌 특수 포맷):
     *   buf[feature_idx * numDet + det_idx]
     *
     *   feature 0~3: bbox (cx, cy, w, h) — inputSize px 단위
     *   feature 4~(4+numClasses-1): 각 클래스의 confidence score
     *
     * 각 박스 처리:
     *   1. 가장 높은 클래스 score 찾기
     *   2. confThreshold 미만이면 버림 (낮은 확신도 제거)
     *   3. COCO_KO 맵에서 한국어 이름 찾기
     *   4. NMS로 겹치는 박스 제거
     */
    private fun postProcess(values: FloatArray, numFeatures: Int, numDet: Int): PostProcessResult {
        val numClasses = numFeatures - 4  // bbox 4개를 제외한 나머지 = 클래스 수
        val candidates = mutableListOf<Detection>()

        for (i in 0 until numDet) {
            var maxScore = confThreshold  // 이 값 미만은 바로 버림
            var maxClass = -1

            for (c in 0 until numClasses) {
                val s = values[(4 + c) * numDet + i]  // 클래스 c의 score
                if (s > maxScore) { maxScore = s; maxClass = c }
            }
            if (maxClass < 0) continue  // confThreshold 넘은 클래스 없음 → 버림

            val name = COCO_KO[maxClass] ?: continue  // 한국어 이름 없으면 버림

            candidates.add(Detection(
                classKo    = name,
                confidence = maxScore,
                // YOLO 출력은 inputSize px 단위 → 0~1 정규화
                cx = values[i] / inputSize,
                cy = values[numDet + i] / inputSize,
                w  = values[2 * numDet + i] / inputSize,
                h  = values[3 * numDet + i] / inputSize
            ))
        }

        // confidence 높은 순 정렬 후 NMS 적용, 최대 2개 반환
        val kept = nms(candidates.sortedByDescending { it.confidence }).take(2)
        return PostProcessResult(kept, candidates.size)
    }

    private fun nanosToMs(nanos: Long): Long = nanos / 1_000_000

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
        resizedBitmap.recycle()
        session.close()
        env.close()
    }

    companion object {
        private const val TAG = "YoloDetector"
        private const val MAX_INPUT_POOL_SIZE = 3
        private const val MAX_OUTPUT_POOL_SIZE = 2
        private const val USE_XNNPACK = false
    }
}
