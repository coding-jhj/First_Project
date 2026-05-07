package com.voiceguide

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

enum class VibrationPattern {
    NONE,
    SHORT,
    DOUBLE,
    URGENT
}

enum class EventType { GRADUAL, SUDDEN }

data class MvpFrame(
    val detections: List<Detection>,
    val maxRisk: Float,
    val vibrationPattern: VibrationPattern,
    val shouldSpeak: Boolean
)

class MvpPipeline {
    private data class Track(
        val id: Int,
        var cls: String,
        var cx: Float,
        var cy: Float,
        var w: Float,
        var h: Float,
        var distanceM: Float,
        var prevDistanceM: Float,
        var risk: Float,
        var missed: Int = 0
    )

    private val tracks = mutableListOf<Track>()
    private var nextTrackId = 1
    private val lastSpokenTime = HashMap<Int, Long>()

    fun update(detections: List<Detection>): MvpFrame {
        tracks.forEach { it.missed += 1 }

        val assignedTrackIds = mutableSetOf<Int>()
        val assignedDetectionIds = mutableSetOf<Int>()
        val output = mutableListOf<Detection>()
        val newTrackIds = mutableSetOf<Int>()

        val scoredPairs = mutableListOf<Triple<Float, Int, Int>>()
        for (di in detections.indices) {
            for (ti in tracks.indices) {
                val tr = tracks[ti]
                if (tr.cls != detections[di].classKo) continue
                val score = iou(detections[di], tr)
                if (score >= IOU_MATCH_THRESHOLD) scoredPairs.add(Triple(score, di, ti))
            }
        }

        for ((_, di, ti) in scoredPairs.sortedByDescending { it.first }) {
            if (di in assignedDetectionIds) continue
            val track = tracks[ti]
            if (track.id in assignedTrackIds) continue
            assignedDetectionIds.add(di)
            assignedTrackIds.add(track.id)
            output.add(updateTrack(track, detections[di]))
        }

        for (di in detections.indices) {
            if (di in assignedDetectionIds) continue
            val det = detections[di]
            val risk = computeRisk(det)
            val distanceM = bboxDistanceM(det)
            val track = Track(
                id = nextTrackId++,
                cls = det.classKo,
                cx = det.cx,
                cy = det.cy,
                w = det.w,
                h = det.h,
                distanceM = distanceM,
                prevDistanceM = distanceM,
                risk = risk,
                missed = 0
            )
            tracks.add(track)
            newTrackIds.add(track.id)
            output.add(withMvpFields(det, track.id, distanceM, risk))
        }

        tracks.removeAll { it.missed > MAX_MISSED_FRAMES }
        val activeIds = tracks.map { it.id }.toSet()
        lastSpokenTime.keys.removeAll { it !in activeIds }

        val sorted = output.sortedWith(
            compareByDescending<Detection> { it.riskScore }
                .thenByDescending { it.w * it.h }
        )
        val maxRisk = sorted.maxOfOrNull { it.riskScore } ?: 0f
        val pattern = patternFor(maxRisk, sorted.firstOrNull())
        val trackMap = tracks.associateBy { it.id }
        val shouldSpeak = computeShouldSpeak(sorted, newTrackIds, pattern, trackMap)

        return MvpFrame(
            detections = sorted,
            maxRisk = maxRisk,
            vibrationPattern = pattern,
            shouldSpeak = shouldSpeak
        )
    }

    private fun updateTrack(track: Track, det: Detection): Detection {
        val rawDistance = bboxDistanceM(det)
        val rawRisk = computeRisk(det)

        track.prevDistanceM = track.distanceM  // 접근속도 계산을 위해 이전값 보존
        track.cx = EMA_ALPHA * det.cx + (1f - EMA_ALPHA) * track.cx
        track.cy = EMA_ALPHA * det.cy + (1f - EMA_ALPHA) * track.cy
        track.w = EMA_ALPHA * det.w + (1f - EMA_ALPHA) * track.w
        track.h = EMA_ALPHA * det.h + (1f - EMA_ALPHA) * track.h
        track.distanceM = EMA_ALPHA * rawDistance + (1f - EMA_ALPHA) * track.distanceM
        track.risk = EMA_ALPHA * rawRisk + (1f - EMA_ALPHA) * track.risk
        track.missed = 0

        return withMvpFields(
            det.copy(cx = track.cx, cy = track.cy, w = track.w, h = track.h),
            track.id,
            track.distanceM,
            track.risk
        )
    }

    private fun withMvpFields(
        det: Detection,
        trackId: Int,
        distanceM: Float,
        risk: Float
    ): Detection {
        return det.copy(
            trackId = trackId,
            riskScore = risk.coerceIn(0f, 1f),
            vibrationPattern = patternFor(risk, det).name,
            distanceM = distanceM
        )
    }

    private fun bboxDistanceM(det: Detection): Float {
        val area = (det.w * det.h).coerceAtLeast(0.0001f)
        return sqrt(BBOX_CALIB_AREA / area).coerceIn(0.2f, 20f)
    }

    private fun computeRisk(det: Detection): Float {
        val distanceM = bboxDistanceM(det)
        val area = det.w * det.h
        val centerWeight = 1f - min(0.6f, abs(det.cx - 0.5f) * 1.2f)
        val distanceWeight = when {
            distanceM <= 0.8f -> 1.0f
            distanceM <= 1.5f -> 0.85f
            distanceM <= 2.5f -> 0.65f
            distanceM <= 4.0f -> 0.35f
            else -> 0.15f
        }
        val classWeight = when {
            det.classKo in VoicePolicy.vehicleKo() -> 1.0f
            det.classKo in VoicePolicy.animalKo() -> 0.85f
            det.classKo in VoicePolicy.criticalKo() -> 0.9f
            det.classKo in VoicePolicy.cautionKo() -> 0.65f
            else -> 0.45f
        }
        val sizeBoost = min(0.25f, area * 1.8f)
        return (centerWeight * distanceWeight * classWeight + sizeBoost).coerceIn(0f, 1f)
    }

    private fun patternFor(risk: Float, det: Detection?): VibrationPattern {
        if (det != null && det.classKo in VoicePolicy.vehicleKo() && risk >= 0.55f) {
            return VibrationPattern.URGENT
        }
        return when {
            risk >= 0.75f -> VibrationPattern.URGENT
            risk >= 0.55f -> VibrationPattern.DOUBLE
            risk >= 0.35f -> VibrationPattern.SHORT
            else -> VibrationPattern.NONE
        }
    }

    // 이벤트 타입 판단: 측면, 빠른 접근, 신규 근접 등장 → SUDDEN
    private fun eventTypeFor(det: Detection, track: Track, isNew: Boolean): EventType {
        if (det.cx < SIDE_LEFT_THRESHOLD || det.cx > SIDE_RIGHT_THRESHOLD) return EventType.SUDDEN
        if (isNew && track.distanceM <= NEW_TRACK_SUDDEN_DIST_M) return EventType.SUDDEN
        if (!isNew) {
            val delta = track.prevDistanceM - track.distanceM  // 양수 = 접근 중
            if (delta >= FAST_APPROACH_DELTA_M) return EventType.SUDDEN
        }
        return EventType.GRADUAL
    }

    // URGENT는 항상 발화. SUDDEN은 진동만. GRADUAL은 5초 쿨다운 적용.
    private fun computeShouldSpeak(
        detections: List<Detection>,
        newTrackIds: Set<Int>,
        pattern: VibrationPattern,
        trackMap: Map<Int, Track>
    ): Boolean {
        if (pattern == VibrationPattern.URGENT) return true
        if (detections.isEmpty()) return false

        val now = System.currentTimeMillis()
        for (det in detections) {
            val track = trackMap[det.trackId] ?: continue
            val isNew = det.trackId in newTrackIds
            if (eventTypeFor(det, track, isNew) == EventType.SUDDEN) continue
            val lastTime = lastSpokenTime[det.trackId] ?: 0L
            if (now - lastTime < SPEAK_COOLDOWN_MS) continue
            lastSpokenTime[det.trackId] = now
            return true
        }
        return false
    }

    private fun iou(det: Detection, track: Track): Float {
        val ax1 = det.cx - det.w / 2f
        val ay1 = det.cy - det.h / 2f
        val ax2 = det.cx + det.w / 2f
        val ay2 = det.cy + det.h / 2f
        val bx1 = track.cx - track.w / 2f
        val by1 = track.cy - track.h / 2f
        val bx2 = track.cx + track.w / 2f
        val by2 = track.cy + track.h / 2f

        val ix = max(0f, min(ax2, bx2) - max(ax1, bx1))
        val iy = max(0f, min(ay2, by2) - max(ay1, by1))
        val inter = ix * iy
        val union = det.w * det.h + track.w * track.h - inter
        return if (union > 0f) inter / union else 0f
    }

    companion object {
        private const val IOU_MATCH_THRESHOLD = 0.25f
        private const val MAX_MISSED_FRAMES = 12
        private const val EMA_ALPHA = 0.55f
        private const val BBOX_CALIB_AREA = 0.06f
        private const val SIDE_LEFT_THRESHOLD = 0.33f
        private const val SIDE_RIGHT_THRESHOLD = 0.67f
        private const val NEW_TRACK_SUDDEN_DIST_M = 2f
        private const val FAST_APPROACH_DELTA_M = 0.8f
        private const val SPEAK_COOLDOWN_MS = 5000L
    }
}
