package com.voiceguide

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View
import java.util.Locale
import kotlin.math.max
import kotlin.math.min

class BoundingBoxOverlay @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    private var detections: List<Detection> = emptyList()

    private val boxPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.rgb(0, 229, 255)
        style = Paint.Style.STROKE
        strokeWidth = 5f
    }

    private val labelBgPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.argb(210, 0, 0, 0)
        style = Paint.Style.FILL
    }

    private val labelTextPaint = Paint(Paint.ANTI_ALIAS_FLAG).apply {
        color = Color.WHITE
        textSize = 38f
        textAlign = Paint.Align.LEFT
        typeface = android.graphics.Typeface.DEFAULT_BOLD
    }

    fun setDetections(items: List<Detection>) {
        detections = items
        invalidate()
    }

    fun clear() {
        detections = emptyList()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        if (detections.isEmpty()) return

        for (det in detections) {
            val left = ((det.cx - det.w / 2f) * width).coerceIn(0f, width.toFloat())
            val top = ((det.cy - det.h / 2f) * height).coerceIn(0f, height.toFloat())
            val right = ((det.cx + det.w / 2f) * width).coerceIn(0f, width.toFloat())
            val bottom = ((det.cy + det.h / 2f) * height).coerceIn(0f, height.toFloat())

            if (right <= left || bottom <= top) continue

            canvas.drawRect(RectF(left, top, right, bottom), boxPaint)

            val label = String.format(
                Locale.KOREA,
                "%s %.0f%%",
                det.classKo,
                det.confidence * 100f
            )
            val paddingX = 12f
            val paddingY = 8f
            val textWidth = labelTextPaint.measureText(label)
            val textHeight = labelTextPaint.textSize
            val labelLeft = left
            val labelTop = max(0f, top - textHeight - paddingY * 2f)
            val labelRight = min(width.toFloat(), labelLeft + textWidth + paddingX * 2f)
            val labelBottom = labelTop + textHeight + paddingY * 2f

            canvas.drawRoundRect(
                RectF(labelLeft, labelTop, labelRight, labelBottom),
                8f,
                8f,
                labelBgPaint
            )
            canvas.drawText(label, labelLeft + paddingX, labelBottom - paddingY - 6f, labelTextPaint)
        }
    }
}
