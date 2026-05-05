package com.voiceguide

import android.content.Context
import android.util.Log
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import kotlin.math.round
import kotlin.math.sqrt

/**
 * 서버 policy.json SSOT를 온디바이스에 반영.
 */
object VoicePolicy {

    private const val PREFS = "voiceguide"
    private const val PREF_POLICY_JSON = "cached_policy_json"
    private const val SUPPORTED_VERSION = 1

    data class Snap(
        val version: Int,
        val vehicleKo: Set<String>, val animalKo: Set<String>, val cautionKo: Set<String>,
        val everydayKo: Set<String>, val criticalKo: Set<String>, val voteBypassKo: Set<String>,
        val vehicleCriticalM: Double, val animalCriticalM: Double,
        val bboxCalibArea: Float, val nearVehicleAreaRatio: Float, val cautionAreaRatio: Float,
        val findHazardAreaRatio: Float, val findHazardAreaMultiplier: Float,
        val heldAreaInHand: Float, val heldAreaFront: Float, val heldAreaNear: Float,
        val clampMinM: Double, val clampMaxM: Double, val closeFaceM: Double, val halfMeterUntilM: Double,
        val meterSuffix: String, val heldInHandMaxM: Double, val heldFrontMaxM: Double, val heldNearMaxM: Double,
    )

    @Volatile
    private var snap: Snap? = null

    private fun requireSnap(): Snap = snap ?: error("VoicePolicy.init()가 호출되지 않았습니다.")

    fun vehicleKo(): Set<String> = requireSnap().vehicleKo
    fun animalKo(): Set<String> = requireSnap().animalKo
    fun cautionKo(): Set<String> = requireSnap().cautionKo
    fun everydayKo(): Set<String> = requireSnap().everydayKo
    fun criticalKo(): Set<String> = requireSnap().criticalKo
    fun voteBypassKo(): Set<String> = requireSnap().voteBypassKo

    fun nearVehicleAreaRatio(): Float = requireSnap().nearVehicleAreaRatio
    fun cautionAreaRatio(): Float = requireSnap().cautionAreaRatio
    fun findHazardAreaRatio(): Float = requireSnap().findHazardAreaRatio
    fun findHazardAreaMultiplier(): Float = requireSnap().findHazardAreaMultiplier
    fun heldAreaInHand(): Float = requireSnap().heldAreaInHand
    fun heldAreaFront(): Float = requireSnap().heldAreaFront
    fun heldAreaNear(): Float = requireSnap().heldAreaNear

    fun init(appContext: Context) {
        if (snap != null) return
        synchronized(this) {
            if (snap != null) return
            val prefs = appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            val cached = prefs.getString(PREF_POLICY_JSON, null)
            val json = when {
                !cached.isNullOrBlank() -> cached
                else -> appContext.assets.open("policy_default.json").bufferedReader().use { it.readText() }
            }
            snap = parsePolicy(json)
        }
    }

    fun applyFromServerJson(appContext: Context, json: String) {
        val next = try {
            val root = JSONObject(json)
            val version = root.optInt("version", 1)
            if (version > SUPPORTED_VERSION) {
                Log.w("VoicePolicy", "지원하지 않는 상위 버전 정책입니다 (버전: $version). 캐시를 유지합니다.")
                return
            }
            parsePolicy(json)
        } catch (e: Exception) {
            Log.e("VoicePolicy", "서버 정책 JSON 파싱 실패! 원인: ${e.message}", e)
            return
        }
        
        snap = next
        appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(PREF_POLICY_JSON, json)
            .apply()
    }

    fun formatDistMeters(distM: Double): String {
        val s = requireSnap()
        var d = distM.coerceIn(s.clampMinM, s.clampMaxM)
        if (d < s.closeFaceM) return "코앞"
        if (d < s.halfMeterUntilM) {
            val r = round(d * 2.0) / 2.0
            val str = String.format(Locale.US, "%.1f", r).trimEnd('0').trimEnd('.')
            return "약 $str${s.meterSuffix}"
        }
        val r = round(d).toInt()
        return "약 $r${s.meterSuffix}"
    }

    fun formatDistBbox(w: Float, h: Float): String {
        val s = requireSnap()
        val area = w * h
        val calib = s.bboxCalibArea.toDouble()
        val dist = if (area > 0f) sqrt(calib / area) else 99.0
        return formatDistMeters(dist)
    }

    private fun parsePolicy(raw: String): Snap {
        val root = JSONObject(raw)
        val classes = root.getJSONObject("classes")
        fun strSet(key: String): Set<String> {
            val arr: JSONArray = classes.getJSONArray(key)
            return (0 until arr.length()).map { arr.getString(it) }.toSet()
        }
        val alert = root.getJSONObject("alert_mode")
        val df = root.getJSONObject("distance_format")
        val held = root.getJSONObject("held_sentence_m")
        val od = root.getJSONObject("on_device")
        return Snap(
            version = root.optInt("version", 1),
            vehicleKo = strSet("vehicle_ko"),
            animalKo = strSet("animal_ko"),
            cautionKo = strSet("caution_ko"),
            everydayKo = strSet("everyday_ko"),
            criticalKo = strSet("critical_ko"),
            voteBypassKo = strSet("vote_bypass_ko"),
            vehicleCriticalM = alert.getDouble("vehicle_critical_m"),
            animalCriticalM = alert.getDouble("animal_critical_m"),
            bboxCalibArea = od.getDouble("bbox_calib_area").toFloat(),
            nearVehicleAreaRatio = od.getDouble("near_vehicle_area_ratio").toFloat(),
            cautionAreaRatio = od.getDouble("caution_area_ratio").toFloat(),
            findHazardAreaRatio = od.getDouble("find_hazard_area_ratio").toFloat(),
            findHazardAreaMultiplier = od.getDouble("find_hazard_area_multiplier").toFloat(),
            heldAreaInHand = od.getDouble("held_area_in_hand").toFloat(),
            heldAreaFront = od.getDouble("held_area_front").toFloat(),
            heldAreaNear = od.getDouble("held_area_near").toFloat(),
            clampMinM = df.getDouble("clamp_min_m"),
            clampMaxM = df.getDouble("clamp_max_m"),
            closeFaceM = df.getDouble("close_face_m"),
            halfMeterUntilM = df.getDouble("half_meter_round_until_m"),
            meterSuffix = df.getString("meter_suffix"),
            heldInHandMaxM = held.getDouble("in_hand_max_m"),
            heldFrontMaxM = held.getDouble("immediate_front_max_m"),
            heldNearMaxM = held.getDouble("near_max_m"),
        )
    }
}