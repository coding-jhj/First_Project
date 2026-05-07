package com.voiceguide

import android.content.Context
import android.graphics.Bitmap
import java.nio.ByteBuffer
import java.nio.ByteOrder
import org.tensorflow.lite.Interpreter

class TfliteYoloDetector(context: Context) {
    private val interpreter: Interpreter
    val modelName: String
    val executionProvider: String = "TFLite-XNNPACK"
    private val inputSize: Int
    private val outputRows: Int
    private val outputCols: Int
    private val confThreshold = 0.40f
    private val iouThreshold = 0.45f
    private var outputShapeLogged = false

    init {
        modelName = listOf("yolo26n_float32.tflite").first { name ->
            try {
                context.assets.open(name).close()
                true
            } catch (_: Exception) {
                false
            }
        }
        val modelBytes = context.assets.open(modelName).readBytes()
        val modelBuffer = ByteBuffer.allocateDirect(modelBytes.size).order(ByteOrder.nativeOrder())
        modelBuffer.put(modelBytes)
        modelBuffer.rewind()

        interpreter = Interpreter(modelBuffer, Interpreter.Options().apply {
            setNumThreads(4)
            setUseXNNPACK(true)
        })

        val inputShape = interpreter.getInputTensor(0).shape()
        inputSize = inputShape.getOrNull(1) ?: 320
        val outputShape = interpreter.getOutputTensor(0).shape()
        outputRows = outputShape.getOrNull(1) ?: 300
        outputCols = outputShape.getOrNull(2) ?: 6
        android.util.Log.d(
            "VG_PERF",
            "YOLO input model=$modelName provider=$executionProvider size=${inputSize}x$inputSize shape=${inputShape.joinToString(prefix = "[", postfix = "]")}"
        )
    }

    @Synchronized
    fun detect(bitmap: Bitmap): List<Detection> {
        val origW = bitmap.width
        val origH = bitmap.height
        val scale = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
        val scaledW = (origW * scale + 0.5f).toInt()
        val scaledH = (origH * scale + 0.5f).toInt()
        val padX = (inputSize - scaledW) / 2
        val padY = (inputSize - scaledH) / 2

        val letterboxed = Bitmap.createBitmap(inputSize, inputSize, Bitmap.Config.ARGB_8888)
        val lbCanvas = android.graphics.Canvas(letterboxed)
        lbCanvas.drawARGB(255, 0, 0, 0)
        val scaled = Bitmap.createScaledBitmap(bitmap, scaledW, scaledH, true)
        lbCanvas.drawBitmap(scaled, padX.toFloat(), padY.toFloat(), null)
        scaled.recycle()

        val inputBuffer = bitmapToNHWC(letterboxed)
        letterboxed.recycle()
        return runModel(inputBuffer, padX, padY, scaledW, scaledH)
    }

    @Synchronized
    fun detect(frame: YuvFrame): List<Detection> {
        val origW = frame.displayWidth
        val origH = frame.displayHeight
        val scale = minOf(inputSize.toFloat() / origW, inputSize.toFloat() / origH)
        val scaledW = (origW * scale + 0.5f).toInt()
        val scaledH = (origH * scale + 0.5f).toInt()
        val padX = (inputSize - scaledW) / 2
        val padY = (inputSize - scaledH) / 2
        val inputBuffer = yuvToNHWC(frame, scale, padX, padY, scaledW, scaledH)
        return runModel(inputBuffer, padX, padY, scaledW, scaledH)
    }

    private fun runModel(
        inputBuffer: ByteBuffer,
        padX: Int,
        padY: Int,
        scaledW: Int,
        scaledH: Int
    ): List<Detection> {
        inputBuffer.rewind()
        val output = Array(1) { Array(outputRows) { FloatArray(outputCols) } }
        interpreter.run(inputBuffer, output)
        if (!outputShapeLogged) {
            outputShapeLogged = true
            android.util.Log.d(
                "VG_PERF",
                "YOLO output model=$modelName provider=$executionProvider shape=[1, $outputRows, $outputCols]"
            )
        }
        return postProcessEndToEnd(output[0], padX, padY, scaledW, scaledH)
    }

    private fun bitmapToNHWC(bitmap: Bitmap): ByteBuffer {
        val pixels = IntArray(inputSize * inputSize)
        bitmap.getPixels(pixels, 0, inputSize, 0, 0, inputSize, inputSize)
        val buffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3).order(ByteOrder.nativeOrder())
        for (pixel in pixels) {
            buffer.putFloat(((pixel shr 16) and 0xFF) / 255f)
            buffer.putFloat(((pixel shr 8) and 0xFF) / 255f)
            buffer.putFloat((pixel and 0xFF) / 255f)
        }
        buffer.rewind()
        return buffer
    }

    private fun yuvToNHWC(
        frame: YuvFrame,
        scale: Float,
        padX: Int,
        padY: Int,
        scaledW: Int,
        scaledH: Int
    ): ByteBuffer {
        val buffer = ByteBuffer.allocateDirect(4 * inputSize * inputSize * 3).order(ByteOrder.nativeOrder())
        val rotation = ((frame.rotationDegrees % 360) + 360) % 360

        for (y in padY until padY + scaledH) {
            val srcDisplayY = ((y - padY) / scale).toInt().coerceIn(0, frame.displayHeight - 1)
            for (x in padX until padX + scaledW) {
                val srcDisplayX = ((x - padX) / scale).toInt().coerceIn(0, frame.displayWidth - 1)
                val srcX: Int
                val srcY: Int
                when (rotation) {
                    90 -> {
                        srcX = srcDisplayY.coerceIn(0, frame.width - 1)
                        srcY = (frame.height - 1 - srcDisplayX).coerceIn(0, frame.height - 1)
                    }
                    180 -> {
                        srcX = (frame.width - 1 - srcDisplayX).coerceIn(0, frame.width - 1)
                        srcY = (frame.height - 1 - srcDisplayY).coerceIn(0, frame.height - 1)
                    }
                    270 -> {
                        srcX = (frame.width - 1 - srcDisplayY).coerceIn(0, frame.width - 1)
                        srcY = srcDisplayX.coerceIn(0, frame.height - 1)
                    }
                    else -> {
                        srcX = srcDisplayX.coerceIn(0, frame.width - 1)
                        srcY = srcDisplayY.coerceIn(0, frame.height - 1)
                    }
                }
                val yIndex = srcY * frame.width + srcX
                val uvIndex = frame.width * frame.height + (srcY / 2) * frame.width + (srcX / 2) * 2
                val yy = (frame.nv21[yIndex].toInt() and 0xFF).coerceAtLeast(16)
                val vv = (frame.nv21[uvIndex].toInt() and 0xFF) - 128
                val uu = (frame.nv21[uvIndex + 1].toInt() and 0xFF) - 128
                val c = yy - 16
                val r = ((298 * c + 409 * vv + 128) shr 8).coerceIn(0, 255)
                val g = ((298 * c - 100 * uu - 208 * vv + 128) shr 8).coerceIn(0, 255)
                val b = ((298 * c + 516 * uu + 128) shr 8).coerceIn(0, 255)
                val offset = (y * inputSize + x) * 3 * 4
                buffer.putFloat(offset, r / 255f)
                buffer.putFloat(offset + 4, g / 255f)
                buffer.putFloat(offset + 8, b / 255f)
            }
        }
        buffer.rewind()
        return buffer
    }

    private fun postProcessEndToEnd(
        rows: Array<FloatArray>,
        padX: Int,
        padY: Int,
        scaledW: Int,
        scaledH: Int
    ): List<Detection> {
        val candidates = mutableListOf<Detection>()
        for (row in rows) {
            if (row.size < 6) continue
            var x1 = row[0]
            var y1 = row[1]
            var x2 = row[2]
            var y2 = row[3]
            val score = row[4]
            val classId = row[5].toInt()
            if (score < confThreshold) continue
            val name = COCO_KO[classId] ?: continue

            if (maxOf(kotlin.math.abs(x1), kotlin.math.abs(y1), kotlin.math.abs(x2), kotlin.math.abs(y2)) <= 2f) {
                x1 *= inputSize
                y1 *= inputSize
                x2 *= inputSize
                y2 *= inputSize
            }

            val cx = (((x1 + x2) / 2f) - padX) / scaledW
            val cy = (((y1 + y2) / 2f) - padY) / scaledH
            val w = (x2 - x1) / scaledW
            val h = (y2 - y1) / scaledH
            if (cx < 0f || cx > 1f || cy < 0f || cy > 1f || w <= 0f || h <= 0f) continue

            candidates.add(Detection(
                classKo = name,
                confidence = score,
                cx = cx,
                cy = cy,
                w = w,
                h = h
            ))
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
        val ax1 = a.cx - a.w / 2f
        val ay1 = a.cy - a.h / 2f
        val ax2 = a.cx + a.w / 2f
        val ay2 = a.cy + a.h / 2f
        val bx1 = b.cx - b.w / 2f
        val by1 = b.cy - b.h / 2f
        val bx2 = b.cx + b.w / 2f
        val by2 = b.cy + b.h / 2f
        val iw = maxOf(0f, minOf(ax2, bx2) - maxOf(ax1, bx1))
        val ih = maxOf(0f, minOf(ay2, by2) - maxOf(ay1, by1))
        val inter = iw * ih
        val union = a.w * a.h + b.w * b.h - inter
        return if (union > 0f) inter / union else 0f
    }

    fun close() {
        interpreter.close()
    }
}
