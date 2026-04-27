package com.voiceguide

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.util.AttributeSet
import android.view.View

/**
 * 디버깅용 바운드박스 오버레이 View.
 * 카메라 프리뷰 위에 겹쳐서 배치되며, YOLO 탐지 결과를
 * 사각형과 레이블(클래스명 + 신뢰도)로 시각화한다.
 */
class BoundingBoxOverlay @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : View(context, attrs) {

    // 바운드박스 테두리용 Paint (외곽선만 그림)
    private val boxPaint = Paint().apply {
        style = Paint.Style.STROKE
        strokeWidth = 4f
        isAntiAlias = true
    }

    // 클래스명 + 신뢰도 텍스트용 Paint
    private val textPaint = Paint().apply {
        textSize = 36f
        isAntiAlias = true
        style = Paint.Style.FILL
        isFakeBoldText = true
    }

    // 텍스트 뒤에 깔리는 반투명 검정 배경 Paint (가독성 향상)
    private val bgPaint = Paint().apply {
        style = Paint.Style.FILL
        color = Color.argb(160, 0, 0, 0)
    }

    // 탐지 결과가 여러 개일 때 각 박스를 구별하기 위한 색상 팔레트
    private val colors = intArrayOf(
        Color.RED,
        Color.GREEN,
        Color.CYAN,
        Color.YELLOW,
        Color.MAGENTA,
        Color.WHITE
    )

    // 현재 화면에 그릴 탐지 결과 목록
    private var detections: List<Detection> = emptyList()

    // 추론에 사용된 원본 이미지 크기 (EXIF 회전 적용 후)
    private var imageWidth  = 0
    private var imageHeight = 0

    /**
     * 새 탐지 결과를 받아 화면을 다시 그린다.
     * imgW/imgH는 EXIF 회전이 적용된 원본 이미지 크기 — FILL_CENTER 보정에 사용.
     */
    fun setDetections(detections: List<Detection>, imgW: Int, imgH: Int) {
        this.detections  = detections
        this.imageWidth  = imgW
        this.imageHeight = imgH
        invalidate()
    }

    /** 분석 중지 시 오버레이를 비운다. */
    fun clearDetections() {
        detections = emptyList()
        invalidate()
    }

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        val vw = width.toFloat()
        val vh = height.toFloat()
        if (vw == 0f || vh == 0f || imageWidth == 0 || imageHeight == 0) return

        // PreviewView의 기본 ScaleType = FILL_CENTER:
        // 이미지를 비율 유지하며 뷰를 꽉 채우고 넘치는 부분은 잘라냄.
        // 탐지 좌표(원본 이미지 [0,1])를 뷰 픽셀로 정확히 변환하기 위해
        // 동일한 변환을 직접 계산한다.
        val scaleX = vw / imageWidth
        val scaleY = vh / imageHeight
        val fillScale  = maxOf(scaleX, scaleY)        // FILL_CENTER: 더 큰 비율로 채움
        val displayW   = imageWidth  * fillScale
        val displayH   = imageHeight * fillScale
        val offsetX    = (vw - displayW) / 2f          // 음수 → 좌우 잘림
        val offsetY    = (vh - displayH) / 2f          // 음수 → 상하 잘림

        detections.forEachIndexed { i, det ->
            val color = colors[i % colors.size]
            boxPaint.color  = color
            textPaint.color = color

            // [0,1] 정규화 좌표 → 뷰 픽셀 (FILL_CENTER 오프셋 포함)
            val left   = offsetX + (det.cx - det.w / 2f) * displayW
            val top    = offsetY + (det.cy - det.h / 2f) * displayH
            val right  = offsetX + (det.cx + det.w / 2f) * displayW
            val bottom = offsetY + (det.cy + det.h / 2f) * displayH

            canvas.drawRect(RectF(left, top, right, bottom), boxPaint)

            val label = "${det.classKo} ${"%.0f".format(det.confidence * 100)}%"
            val textH = textPaint.textSize
            val textW = textPaint.measureText(label)

            val labelY = if (top > textH + 8f) top - 4f else bottom + textH + 4f

            canvas.drawRect(
                left, labelY - textH - 2f,
                left + textW + 10f, labelY + 4f,
                bgPaint
            )
            canvas.drawText(label, left + 5f, labelY, textPaint)
        }
    }
}
