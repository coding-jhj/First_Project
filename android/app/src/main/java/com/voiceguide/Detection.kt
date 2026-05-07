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

data class YuvFrame(
    val nv21: ByteArray,
    val width: Int,
    val height: Int,
    val rotationDegrees: Int
) {
    val displayWidth: Int =
        if (rotationDegrees % 180 == 0) width else height
    val displayHeight: Int =
        if (rotationDegrees % 180 == 0) height else width
}
