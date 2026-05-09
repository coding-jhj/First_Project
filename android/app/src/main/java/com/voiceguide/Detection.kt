package com.voiceguide

data class Detection(
    val classKo: String,
    val confidence: Float,
    val cx: Float,
    val cy: Float,
    val w: Float,
    val h: Float,
    val isFound: Boolean = false,
    val trackId: Int = 0,
    val riskScore: Float = 0f,
    val vibrationPattern: String = "NONE",
    val distanceM: Float = 0f
)

data class TfliteDetectionResult(
    val detections: List<Detection>,
    val preprocessMs: Long,
    val inferMs: Long,
    val postprocessMs: Long
)
