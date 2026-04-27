package com.voiceguide

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import android.content.Context
import android.graphics.Bitmap
import java.nio.FloatBuffer

data class Detection(
    val classKo: String,
    val confidence: Float,
    val cx: Float,   // [0, 1]
    val cy: Float,
    val w: Float,
    val h: Float
)

class YoloDetector(context: Context) {

    private val env = OrtEnvironment.getEnvironment()
    private val session: OrtSession
    private val inputSize = 640
    private val confThreshold = 0.25f
    private val iouThreshold = 0.45f

    init {
        // yolo11m.onnx가 있으면 우선 사용, 없으면 yolo11n.onnx fallback
        val modelName = try {
            context.assets.open("yolo11m.onnx").close(); "yolo11m.onnx"
        } catch (_: Exception) { "yolo11n.onnx" }
        val bytes = context.assets.open(modelName).readBytes()
        session = env.createSession(bytes, OrtSession.SessionOptions())
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

        val inputName = session.inputNames.iterator().next()
        val tensor = OnnxTensor.createTensor(
            env, inputBuffer, longArrayOf(1, 3, inputSize.toLong(), inputSize.toLong())
        )

        val output = session.run(mapOf(inputName to tensor))
        val outputTensor = output[0] as ai.onnxruntime.OnnxTensor
        val shape       = outputTensor.info.shape  // [1, numFeatures, 8400]
        val numFeatures = shape[1].toInt()
        val numDet      = shape[2].toInt()
        val flatBuf     = outputTensor.floatBuffer

        tensor.close()
        output.close()

        return postProcess(flatBuf, numFeatures, numDet, padX, padY, scaledW, scaledH)
    }

    private fun bitmapToNCHW(bitmap: Bitmap): FloatBuffer {
        val pixels = IntArray(inputSize * inputSize)
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)

        val buf = FloatBuffer.allocate(3 * inputSize * inputSize)
        val r = FloatArray(inputSize * inputSize)
        val g = FloatArray(inputSize * inputSize)
        val b = FloatArray(inputSize * inputSize)

        for (i in pixels.indices) {
            r[i] = ((pixels[i] shr 16) and 0xFF) / 255f
            g[i] = ((pixels[i] shr 8)  and 0xFF) / 255f
            b[i] = ((pixels[i])        and 0xFF) / 255f
        }

        buf.put(r); buf.put(g); buf.put(b)
        buf.rewind()
        return buf
    }

    private fun postProcess(
        buf: java.nio.FloatBuffer,
        numFeatures: Int, numDet: Int,
        padX: Int, padY: Int, scaledW: Int, scaledH: Int
    ): List<Detection> {
        // buf layout: [feature_0 * 8400, ..., feature_(numFeatures-1) * 8400]
        // numFeatures = 4(bbox) + numClasses (84 for COCO80, 85 for fine-tuned 81)
        val numClasses = numFeatures - 4
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

        return nms(candidates.sortedByDescending { it.confidence }).take(2)
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
        val ax1 = a.cx - a.w / 2; val ay1 = a.cy - a.h / 2
        val ax2 = a.cx + a.w / 2; val ay2 = a.cy + a.h / 2
        val bx1 = b.cx - b.w / 2; val by1 = b.cy - b.h / 2
        val bx2 = b.cx + b.w / 2; val by2 = b.cy + b.h / 2
        val iw = maxOf(0f, minOf(ax2, bx2) - maxOf(ax1, bx1))
        val ih = maxOf(0f, minOf(ay2, by2) - maxOf(ay1, by1))
        val inter = iw * ih
        val union = a.w * a.h + b.w * b.h - inter
        return if (union > 0) inter / union else 0f
    }

    fun close() {
        session.close()
        env.close()
    }
}
