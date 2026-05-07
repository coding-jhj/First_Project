package com.voiceguide

import android.content.Context
import android.graphics.Bitmap
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.tensorflow.lite.Interpreter

class TfliteYoloDetector(context: Context) {
    private val interpreter: Interpreter
    val modelName: String
    val executionProvider: String
    private val inputSize: Int
    private val outputRows: Int
    private val outputCols: Int
    private val confThreshold = 0.40f
    private val iouThreshold  = 0.45f
    private var outputShapeLogged = false

    // 매 프레임 할당 제거 — 클래스 생성 시 1회만 할당
    private lateinit var inputBuffer: ByteBuffer
    private lateinit var outputArray: Array<Array<FloatArray>>
    // 패딩 영역 초기화용 제로 배열 — ByteBuffer.put(byte[])가 System.arraycopy 경유 최속
    private lateinit var zeroBytes: ByteArray

    init {
        modelName = listOf("yolo26n_float32.tflite").first { name ->
            try { context.assets.open(name).close(); true }
            catch (_: Exception) { false }
        }
        val modelBytes  = context.assets.open(modelName).readBytes()
        val modelBuffer = ByteBuffer.allocateDirect(modelBytes.size).order(ByteOrder.nativeOrder())
        modelBuffer.put(modelBytes)
        modelBuffer.rewind()

        // 1순위 최적화: NNAPI 델리게이트 (NPU/GPU 가속)
        // NNAPI 지원 기기에서 XNNPACK 대비 2~5× 빠름
        // 미지원 기기(Android 8.0 등)는 catch → XNNPACK fallback
        var provider = "TFLite-XNNPACK"
        val options  = Interpreter.Options().apply {
            setNumThreads(4)
            setUseXNNPACK(true)
            try {
                addDelegate(org.tensorflow.lite.nnapi.NnApiDelegate())
                provider = "TFLite-NNAPI"
            } catch (_: Throwable) {
                // NNAPI 미지원 — XNNPACK으로 그대로 진행
            }
        }
        interpreter      = Interpreter(modelBuffer, options)
        executionProvider = provider

        val inputShape  = interpreter.getInputTensor(0).shape()
        inputSize       = inputShape.getOrNull(1) ?: 320
        val outputShape = interpreter.getOutputTensor(0).shape()
        outputRows      = outputShape.getOrNull(1) ?: 300
        outputCols      = outputShape.getOrNull(2) ?: 6

        // 사전 할당
        val bufBytes  = 4 * inputSize * inputSize * 3
        inputBuffer   = ByteBuffer.allocateDirect(bufBytes).order(ByteOrder.nativeOrder())
        outputArray   = Array(1) { Array(outputRows) { FloatArray(outputCols) } }
        zeroBytes     = ByteArray(bufBytes)  // all zeros — 패딩 영역 초기화용

        android.util.Log.d("VG_PERF",
            "YOLO model=$modelName provider=$executionProvider size=${inputSize}x${inputSize} " +
            "shape=${inputShape.toList()}")
    }

    // @Synchronized 제거 — MAX_ON_DEVICE_IN_FLIGHT=1로 단일 스레드 진입 보장됨
    fun detect(bitmap: Bitmap): List<Detection> {
        val origW   = bitmap.width
        val origH   = bitmap.height
        val scale   = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
        val scaledW = (origW * scale + 0.5f).toInt()
        val scaledH = (origH * scale + 0.5f).toInt()
        val padX    = (inputSize - scaledW) / 2
        val padY    = (inputSize - scaledH) / 2

        val letterboxed = Bitmap.createBitmap(inputSize, inputSize, Bitmap.Config.ARGB_8888)
        val canvas = android.graphics.Canvas(letterboxed)
        canvas.drawARGB(255, 0, 0, 0)
        val scaled = Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)
        canvas.drawBitmap(scaled, padX.toFloat(), padY.toFloat(), null)
        scaled.recycle()

        fillInputFromBitmap(letterboxed)
        letterboxed.recycle()
        return runModel(padX, padY, scaledW, scaledH)
    }

    fun detect(frame: YuvFrame): List<Detection> {
        val origW   = frame.displayWidth
        val origH   = frame.displayHeight
        val scale   = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
        val scaledW = (origW * scale + 0.5f).toInt()
        val scaledH = (origH * scale + 0.5f).toInt()
        val padX    = (inputSize - scaledW) / 2
        val padY    = (inputSize - scaledH) / 2
        fillInputFromYuv(frame, scale, padX, padY, scaledW, scaledH)
        return runModel(padX, padY, scaledW, scaledH)
    }

    private fun runModel(padX: Int, padY: Int, scaledW: Int, scaledH: Int): List<Detection> {
        inputBuffer.rewind()
        interpreter.run(inputBuffer, outputArray)
        if (!outputShapeLogged) {
            outputShapeLogged = true
            android.util.Log.d("VG_PERF",
                "YOLO output model=$modelName provider=$executionProvider shape=[1, $outputRows, $outputCols]")
        }
        return postProcessEndToEnd(outputArray[0], padX, padY, scaledW, scaledH)
    }

    private fun fillInputFromBitmap(bitmap: Bitmap) {
        val pixels = IntArray(inputSize * inputSize)
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)
        inputBuffer.rewind()
        for (pixel in pixels) {
            inputBuffer.putFloat(((pixel shr 16) and 0xFF) / 255f)
            inputBuffer.putFloat(((pixel shr 8)  and 0xFF) / 255f)
            inputBuffer.putFloat((pixel          and 0xFF) / 255f)
        }
    }

    private fun fillInputFromYuv(
        frame: YuvFrame,
        scale: Float,
        padX: Int, padY: Int,
        scaledW: Int, scaledH: Int
    ) {
        // 2순위 최적화 ①: System.arraycopy 경유 제로 초기화 (~1ms) — putFloat(0f) 반복 대비 수 배 빠름
        inputBuffer.rewind()
        inputBuffer.put(zeroBytes)

        val nv21       = frame.nv21
        val frameW     = frame.width
        val frameH     = frame.height
        val rotation   = ((frame.rotationDegrees % 360) + 360) % 360
        // 2순위 최적화 ②: 나눗셈 → 역수 곱셈 (정수 나눗셈보다 빠름)
        val scaleRecip = 1f / scale
        val yuvBase    = frameW * frameH  // Y plane 크기 — UV base 오프셋

        for (y in padY until padY + scaledH) {
            val srcDisplayY = ((y - padY) * scaleRecip).toInt().coerceIn(0, frame.displayHeight - 1)
            for (x in padX until padX + scaledW) {
                val srcDisplayX = ((x - padX) * scaleRecip).toInt().coerceIn(0, frame.displayWidth - 1)
                val srcX: Int
                val srcY: Int
                when (rotation) {
                    90  -> { srcX = srcDisplayY;             srcY = frameH - 1 - srcDisplayX }
                    180 -> { srcX = frameW - 1 - srcDisplayX; srcY = frameH - 1 - srcDisplayY }
                    270 -> { srcX = frameW - 1 - srcDisplayY; srcY = srcDisplayX }
                    else -> { srcX = srcDisplayX;             srcY = srcDisplayY }
                }
                val yIndex = srcY * frameW + srcX
                // 2순위 최적화 ③: UV row base를 외부 루프에서 계산 불가(srcY가 inner에서 변함)
                // → 대신 UV 인덱스를 단일 식으로 합산하고 불필요한 coerceIn 제거
                val uvBase2 = yuvBase + (srcY ushr 1) * frameW + (srcX and -2)

                val yy   = (nv21[yIndex].toInt() and 0xFF) - 16
                val vv   = (nv21[uvBase2].toInt()     and 0xFF) - 128
                val uu   = (nv21[uvBase2 + 1].toInt() and 0xFF) - 128
                val c298 = 298 * yy.coerceAtLeast(0)
                val r    = ((c298 + 409 * vv + 128) ushr 8).coerceIn(0, 255)
                val g    = ((c298 - 100 * uu - 208 * vv + 128) ushr 8).coerceIn(0, 255)
                val b    = ((c298 + 516 * uu + 128) ushr 8).coerceIn(0, 255)

                // 절대 위치 putFloat — 순차 접근 대비 약간 느리지만 패딩 영역 skip 덕분에 총량 감소
                val offset = (y * inputSize + x) * 12  // 12 = 3 channels × 4 bytes
                inputBuffer.putFloat(offset,      r / 255f)
                inputBuffer.putFloat(offset +  4, g / 255f)
                inputBuffer.putFloat(offset +  8, b / 255f)
            }
        }
    }

    private fun postProcessEndToEnd(
        rows: Array<FloatArray>,
        padX: Int, padY: Int,
        scaledW: Int, scaledH: Int
    ): List<Detection> {
        val candidates = mutableListOf<Detection>()
        for (row in rows) {
            if (row.size < 6) continue
            var x1 = row[0]; var y1 = row[1]
            var x2 = row[2]; var y2 = row[3]
            val score   = row[4]
            val classId = row[5].toInt()
            if (score < confThreshold) continue
            val name = COCO_KO[classId] ?: continue

            if (maxOf(kotlin.math.abs(x1), kotlin.math.abs(y1),
                      kotlin.math.abs(x2), kotlin.math.abs(y2)) <= 2f) {
                x1 *= inputSize; y1 *= inputSize
                x2 *= inputSize; y2 *= inputSize
            }
            val cx = (((x1 + x2) / 2f) - padX) / scaledW
            val cy = (((y1 + y2) / 2f) - padY) / scaledH
            val w  = (x2 - x1) / scaledW
            val h  = (y2 - y1) / scaledH
            if (cx < 0f || cx > 1f || cy < 0f || cy > 1f || w <= 0f || h <= 0f) continue

            candidates.add(Detection(classKo = name, confidence = score,
                                     cx = cx, cy = cy, w = w, h = h))
        }
        return nms(candidates.sortedByDescending { it.confidence }).take(8)
    }

    private fun nms(sorted: List<Detection>): List<Detection> {
        val keep = mutableListOf<Detection>()
        val skip = BooleanArray(sorted.size)
        for (i in sorted.indices) {
            if (skip[i]) continue
            keep.add(sorted[i])
            for (j in i + 1 until sorted.size) {
                if (!skip[j] && iou(sorted[i], sorted[j]) > iouThreshold) skip[j] = true
            }
        }
        return keep
    }

    private fun iou(a: Detection, b: Detection): Float {
        val ax1 = a.cx - a.w / 2f; val ax2 = a.cx + a.w / 2f
        val ay1 = a.cy - a.h / 2f; val ay2 = a.cy + a.h / 2f
        val bx1 = b.cx - b.w / 2f; val bx2 = b.cx + b.w / 2f
        val by1 = b.cy - b.h / 2f; val by2 = b.cy + b.h / 2f
        val iw    = maxOf(0f, minOf(ax2, bx2) - maxOf(ax1, bx1))
        val ih    = maxOf(0f, minOf(ay2, by2) - maxOf(ay1, by1))
        val inter = iw * ih
        val union = a.w * a.h + b.w * b.h - inter
        return if (union > 0f) inter / union else 0f
    }

    fun close() { interpreter.close() }
}
