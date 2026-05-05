package com.voiceguide

import android.graphics.Bitmap
import kotlin.math.abs

/**
 * 수평 엣지 반복 패턴으로 계단을 탐지하는 보완 탐지기.
 * yolo11m.onnx가 없을 때만 동작하며, 오탐을 최소화하기 위해
 * 아래 5가지 조건을 모두 통과해야 계단으로 판정한다.
 *
 *  1. 절대 엣지 강도  ≥ 20  (너무 어두운 이미지 제외)
 *  2. SNR(신호 대 잡음)  ≥ 3.5  (타일·카펫 등 전체 균일 패턴 제외)
 *  3. 피크(계단 엣지 라인)  ≥ 4개
 *  4. 피크 간격 규칙성  : 평균 간격 대비 ±30% 초과 비율 ≤ 20%
 *  5. 수평 폭 커버리지  ≥ 55%  (물체 일부 엣지·가구 다리 등 제외)
 */
class StairsDetector {

    fun detect(bitmap: Bitmap): Detection? {
        val maxW = 320
        val scaleF = minOf(1f, maxW.toFloat() / bitmap.width)
        val W = (bitmap.width * scaleF).toInt()
        val H = (bitmap.height * scaleF).toInt()
        if (W < 20 || H < 30) return null

        val small = Bitmap.createScaledBitmap(bitmap, W, H, false)
        val result = analyzeForStairs(small, W, H)
        small.recycle()
        return result
    }

    private fun analyzeForStairs(bmp: Bitmap, W: Int, H: Int): Detection? {
        // 이미지 하단 65% 분석 (계단은 주로 하단에 위치)
        val startY = (H * 0.35f).toInt()
        val analyzeH = H - startY
        if (analyzeH < 24) return null

        val pixels = IntArray(W * H)
        bmp.getPixels(pixels, 0, W, 0, 0, W, H)

        // 행(row)별 수직 방향 밝기 차이 계산
        val stepX = maxOf(1, W / 80)
        val rowEdge = FloatArray(analyzeH)
        for (y in 1 until analyzeH) {
            val absY = startY + y
            var sum = 0f; var cnt = 0
            for (x in 0 until W step stepX) {
                sum += abs(luma(pixels[absY * W + x]) - luma(pixels[(absY - 1) * W + x]))
                cnt++
            }
            rowEdge[y] = if (cnt > 0) sum / cnt else 0f
        }

        val maxEdge  = rowEdge.maxOrNull() ?: return null
        val meanEdge = rowEdge.average().toFloat()

        // ── 조건 1: 절대 엣지 강도 ─────────────────────────────────────────
        if (maxEdge < 20f) return null

        // ── 조건 2: SNR — 피크가 배경 잡음보다 3.5배 이상 강해야 함 ────────
        // 타일·카펫처럼 모든 행에 균일한 엣지가 있으면 SNR이 낮아 여기서 걸림
        if (meanEdge < 1f || maxEdge < meanEdge * 3.5f) return null

        // ── 피크 탐지 ──────────────────────────────────────────────────────
        val threshold   = maxOf(maxEdge * 0.55f, 20f)   // 높은 임계값
        // 계단 한 칸 최소 높이: 분석 영역의 1/15 (약 10px at 240px 이미지)
        val minPeakDist = maxOf(10, analyzeH / 15)
        // 계단 한 칸 최대 높이: 분석 영역의 1/3 초과이면 계단이 아닐 가능성 높음
        val maxPeakDist = analyzeH / 3

        val peaks = mutableListOf<Int>()
        for (y in 2 until analyzeH - 2) {
            if (rowEdge[y] < threshold) continue
            if (rowEdge[y] < rowEdge[y - 1] || rowEdge[y] < rowEdge[y + 1]) continue
            if (peaks.isEmpty() || y - peaks.last() >= minPeakDist) {
                peaks.add(y)
            } else if (rowEdge[y] > rowEdge[peaks.last()]) {
                peaks[peaks.size - 1] = y  // 더 강한 피크로 교체
            }
        }

        // ── 조건 3: 최소 4개 피크 ─────────────────────────────────────────
        if (peaks.size < 4) return null

        // ── 조건 4: 간격 규칙성 ───────────────────────────────────────────
        val spacings   = (1 until peaks.size).map { peaks[it] - peaks[it - 1] }
        val avgSpacing = spacings.average().toFloat()

        if (avgSpacing < 10f) return null           // 너무 좁음 → 텍스처·노이즈
        if (avgSpacing > maxPeakDist.toFloat()) return null  // 너무 넓음 → 계단 아님

        // 간격 편차 ±30% 이내여야 규칙적 / 20% 이상 벗어나면 탈락
        val irregularCount = spacings.count { abs(it - avgSpacing) > avgSpacing * 0.30f }
        if (irregularCount > spacings.size * 0.20f) return null

        // ── 조건 5: 수평 폭 커버리지 ≥ 55% ───────────────────────────────
        // 계단 엣지는 화면 가로 전체에 걸쳐 나타남.
        // 가구 다리·그림자 등 좁은 엣지는 여기서 탈락.
        val spanRatio = computeHorizontalSpan(
            pixels, W, H, startY, peaks, stepX,
            edgeThreshold = maxEdge * 0.25f
        )
        if (spanRatio < 0.55f) return null

        // ── 5가지 조건 모두 통과 → 계단 판정 ─────────────────────────────
        val topY = (startY + peaks.first()).toFloat() / H
        val botY = (startY + peaks.last()).toFloat() / H
        val cy   = (topY + botY) / 2f
        val h    = (botY - topY + 0.12f).coerceIn(0.1f, 0.95f)

        return Detection(
            classKo    = "계단",
            confidence = 0.72f,
            cx = 0.5f,
            cy = cy,
            w  = 0.88f,
            h  = h
        )
    }

    /**
     * 각 피크 행에서 엣지가 가로 폭의 몇 %에 걸쳐 있는지 평균을 반환한다.
     * 계단 엣지는 폭 전체에 걸쳐 나타나고, 가구 다리·그림자는 국소적이다.
     */
    private fun computeHorizontalSpan(
        pixels: IntArray, W: Int, H: Int, startY: Int,
        peaks: List<Int>, stepX: Int, edgeThreshold: Float
    ): Float {
        var totalSpan = 0f
        for (peak in peaks) {
            val absY = startY + peak
            if (absY < 1 || absY >= H) continue
            var edgeCols = 0; var totalCols = 0
            for (x in 0 until W step stepX) {
                val diff = abs(luma(pixels[absY * W + x]) - luma(pixels[(absY - 1) * W + x]))
                if (diff >= edgeThreshold) edgeCols++
                totalCols++
            }
            totalSpan += if (totalCols > 0) edgeCols.toFloat() / totalCols else 0f
        }
        return if (peaks.isNotEmpty()) totalSpan / peaks.size else 0f
    }

    private fun luma(pixel: Int): Float {
        val r = (pixel shr 16) and 0xFF
        val g = (pixel shr 8)  and 0xFF
        val b =  pixel         and 0xFF
        return 0.299f * r + 0.587f * g + 0.114f * b
    }
}
