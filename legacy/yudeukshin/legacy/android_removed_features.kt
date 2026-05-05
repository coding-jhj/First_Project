// [LEGACY] 2026-05-03 삭제된 기능 보존
// 장애물 안내·물건 찾기·물건 확인·질문 모드 외 음성 명령 기능 제거
// 원본 파일: android/app/src/main/java/com/voiceguide/MainActivity.kt

// ── 삭제된 멤버 변수 ──────────────────────────────────────────────────────────
//
//    // ── 약 복용 알림 ─────────────────────────────────────────────────────────
//    private var medicationTimer: java.util.Timer? = null
//
//    // ── GPS 하차 알림 + 현재 위치 (대시보드 지도용) ──────────────────────────
//    private var locationManager: android.location.LocationManager? = null
//    private lateinit var fusedLocationClient: com.google.android.gms.location.FusedLocationProviderClient
//    private var targetBusStop: android.location.Location? = null
//    @Volatile private var lastGpsSentTime = 0L
//    private val locationListener = android.location.LocationListener { loc ->
//        updateCurrentLocation(loc, "listener")
//        // 하차 알림 처리
//        targetBusStop?.let { target ->
//            if (loc.distanceTo(target) < 200f) {
//                speak("내릴 정류장에 거의 다 왔어요. 준비하세요.")
//                stopGpsTracking()
//            }
//        }
//    }

// ── handleSttResult() 내 삭제된 케이스들 ────────────────────────────────────
//
//            "텍스트" -> {
//                speakBuiltIn("텍스트를 인식할게요.")
//                captureForOcr()
//            }
//            "바코드" -> {
//                speakBuiltIn("바코드를 인식할게요.")
//                captureForBarcode()
//            }
//            "색상" -> {
//                speakBuiltIn("색상을 확인할게요.")
//                currentMode = "색상"
//                captureAndProcess()
//            }
//            "밝기" -> {
//                val desc = when {
//                    lastLux < 10  -> "매우 어두워요."
//                    lastLux < 50  -> "조금 어두운 편이에요."
//                    lastLux < 300 -> "적당히 밝아요."
//                    else          -> "매우 밝아요."
//                }
//                speak("현재 밝기는 $desc")
//            }
//            "다시읽기" -> {
//                if (lastSentence.isEmpty()) speak("아직 안내한 내용이 없어요.")
//                else speak(lastSentence)
//            }
//            "볼륨업" -> {
//                val am = getSystemService(AUDIO_SERVICE) as AudioManager
//                am.adjustStreamVolume(AudioManager.STREAM_MUSIC,
//                    AudioManager.ADJUST_RAISE, AudioManager.FLAG_SHOW_UI)
//                speak("소리를 높였어요.")
//            }
//            "볼륨다운" -> {
//                val am = getSystemService(AUDIO_SERVICE) as AudioManager
//                am.adjustStreamVolume(AudioManager.STREAM_MUSIC,
//                    AudioManager.ADJUST_LOWER, AudioManager.FLAG_SHOW_UI)
//                speak("소리를 낮췄어요.")
//            }
//            "중지" -> {
//                stopAnalysis()
//                speak("분석을 잠깐 멈출게요.")
//            }
//            "재시작" -> {
//                if (!isAnalyzing.get()) {
//                    speak("다시 시작할게요.")
//                    handler.postDelayed({ requestPermissions() }, 800)
//                } else speak("이미 분석 중이에요.")
//            }
//            "긴급" -> requestSmsPermission { triggerSOS() }
//            "식사" -> {
//                currentMode = "식사"
//                speak("식사 도우미 모드예요. 식기와 음식 위치를 알려드릴게요.")
//                captureAndProcess()
//            }
//            "옷매칭" -> {
//                speak("옷 매칭을 확인할게요.")
//                captureForClothingAdvice("matching")
//            }
//            "옷패턴" -> {
//                speak("옷 패턴을 확인할게요.")
//                captureForClothingAdvice("pattern")
//            }
//            "돈" -> {
//                speak("지폐를 확인할게요.")
//                captureForCurrency()
//            }
//            "약알림" -> {
//                // "8시에 약 먹어야 해" → 시간 추출
//                val hour = Regex("(\\d{1,2})시").find(text)?.groupValues?.get(1)?.toIntOrNull()
//                if (hour != null) setMedicationAlarm(hour)
//                else speak("몇 시에 약을 드실 건가요? 예 : 8시에 약 먹어야 해.")
//            }
//            "하차알림" -> requestLocationPermission {
//                speak("현재 위치를 기준으로 200미터 이내에 도착하면 알려드릴게요.")
//                startGpsTracking(enableArrivalAlert = true)
//            }
//            "저장" -> {
//                val label = SentenceBuilder.extractLabel(text)
//                    .ifEmpty { "위치_${System.currentTimeMillis() / 1000 % 10000}" }
//                val ssid  = getWifiSsid()
//                if (ssid.isEmpty()) {
//                    speak("WiFi에 연결되어 있지 않아 저장할 수 없어요.")
//                } else {
//                    saveLocation(label, ssid)
//                    speak(SentenceBuilder.buildNavigation("save", label))
//                }
//                currentMode = "장애물"
//            }
//            "위치목록" -> {
//                val locs = getLocations()
//                speak(SentenceBuilder.buildNavigation("list", "", locs.map { it.first }))
//                currentMode = "장애물"
//            }

// ── 삭제된 함수: captureForOcr() ────────────────────────────────────────────
//
//    /**
//     * "글자 읽어줘" 명령 처리 — ML Kit OCR로 카메라 이미지의 텍스트 인식.
//     */
//    private fun captureForOcr() {
//        val file = File.createTempFile("vg_ocr_", ".jpg", cacheDir)
//        imageCapture?.takePicture(
//            ImageCapture.OutputFileOptions.Builder(file).build(),
//            cameraExecutor,
//            object : ImageCapture.OnImageSavedCallback {
//                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
//                    Thread {
//                        try {
//                            val bmp = android.graphics.BitmapFactory.decodeFile(file.absolutePath)
//                            val recognizer = com.google.mlkit.vision.text.korean.KoreanTextRecognizerOptions.Builder().build()
//                                .let { com.google.mlkit.vision.text.TextRecognition.getClient(it) }
//                            val image = com.google.mlkit.vision.common.InputImage.fromBitmap(bmp, 0)
//                            recognizer.process(image)
//                                .addOnSuccessListener { result ->
//                                    val text = result.text.trim()
//                                    if (text.isEmpty()) speak("텍스트를 찾지 못했어요.")
//                                    else speak(text)
//                                    file.delete()
//                                }
//                                .addOnFailureListener { speak("텍스트 인식에 실패했어요."); file.delete() }
//                        } catch (_: Exception) { speak("텍스트 인식에 실패했어요."); file.delete() }
//                    }.start()
//                }
//                override fun onError(e: ImageCaptureException) { speak("사진을 찍지 못했어요.") }
//            })
//    }

// ── 삭제된 함수: captureForBarcode() ────────────────────────────────────────
//
//    /**
//     * "바코드" 명령 처리 — ML Kit Barcode Scanning으로 상품 정보 인식.
//     */
//    private fun captureForBarcode() {
//        val file = File.createTempFile("vg_bc_", ".jpg", cacheDir)
//        imageCapture?.takePicture(
//            ImageCapture.OutputFileOptions.Builder(file).build(),
//            cameraExecutor,
//            object : ImageCapture.OnImageSavedCallback {
//                override fun onImageSaved(output: ImageCapture.OutputFileResults) {
//                    Thread {
//                        try {
//                            val bmp = android.graphics.BitmapFactory.decodeFile(file.absolutePath)
//                            val scanner = com.google.mlkit.vision.barcode.BarcodeScanning.getClient()
//                            val image = com.google.mlkit.vision.common.InputImage.fromBitmap(bmp, 0)
//                            scanner.process(image)
//                                .addOnSuccessListener { barcodes ->
//                                    if (barcodes.isEmpty()) speak("바코드를 찾지 못했어요.")
//                                    else speak("${barcodes[0].displayValue ?: "알 수 없는 상품"}이에요.")
//                                    file.delete()
//                                }
//                                .addOnFailureListener { speak("바코드 인식에 실패했어요."); file.delete() }
//                        } catch (_: Exception) { speak("바코드 인식에 실패했어요."); file.delete() }
//                    }.start()
//                }
//                override fun onError(e: ImageCaptureException) { speak("사진을 찍지 못했어요.") }
//            })
//    }

// ── 삭제된 함수: triggerSOS() ────────────────────────────────────────────────
//
//    private fun triggerSOS() {
//        val vibrator = getSystemService(VIBRATOR_SERVICE) as android.os.Vibrator
//        vibrator.vibrate(android.os.VibrationEffect.createWaveform(
//            longArrayOf(0, 500, 200, 500, 200, 500), -1))
//        speak("보호자에게 도움을 요청할게요.")
//        if (guardianPhone.isEmpty()) {
//            speak("보호자 번호가 설정되어 있지 않아요. 설정에서 먼저 등록해 주세요.")
//            return
//        }
//        if (!hasPerm(Manifest.permission.SEND_SMS)) {
//            speak("문자 발송 권한이 없어요. 앱 설정에서 SMS 권한을 허용해 주세요.")
//            return
//        }
//        try {
//            val sms = android.telephony.SmsManager.getDefault()
//            val msg = "[VoiceGuide 긴급] 도움이 필요합니다. 앱에서 자동 발송된 메시지입니다."
//            sms.sendTextMessage(guardianPhone, null, msg, null, null)
//            speak("${guardianPhone}으로 도움 요청 문자를 보냈어요.")
//        } catch (_: Exception) {
//            speak("문자 발송에 실패했어요. 직접 전화해 주세요.")
//        }
//    }

// ── 삭제된 함수: captureForClothingAdvice() ─────────────────────────────────
//
//    // ── 옷 매칭·패턴 (서버 GPT Vision) ───────────────────────────────
//
//    private fun captureForClothingAdvice(type: String) {
//        val serverUrl = getSavedServerUrl().trimEnd('/')
//        if (serverUrl.isEmpty()) {
//            speak("옷 분석은 서버 연결이 필요해요."); return
//        }
//        val file = File.createTempFile("vg_cloth_", ".jpg", cacheDir)
//        imageCapture?.takePicture(
//            ImageCapture.OutputFileOptions.Builder(file).build(), cameraExecutor,
//            object : ImageCapture.OnImageSavedCallback {
//                override fun onImageSaved(o: ImageCapture.OutputFileResults) {
//                    Thread {
//                        try {
//                            val body = okhttp3.MultipartBody.Builder().setType(okhttp3.MultipartBody.FORM)
//                                .addFormDataPart("image", "cloth.jpg",
//                                    file.asRequestBody("image/jpeg".toMediaType()))
//                                .addFormDataPart("type", type)
//                                .build()
//                            val resp = httpClient.newCall(
//                                okhttp3.Request.Builder().url("$serverUrl/vision/clothing").post(body).build()
//                            ).execute()
//                            val sentence = org.json.JSONObject(resp.body?.string() ?: "{}")
//                                .optString("sentence", "분석하지 못했어요.")
//                            runOnUiThread { speak(sentence) }
//                        } catch (_: Exception) { runOnUiThread { speak("옷 분석에 실패했어요.") } }
//                        finally { file.delete() }
//                    }.start()
//                }
//                override fun onError(e: ImageCaptureException) { speak("사진을 찍지 못했어요.") }
//            })
//    }

// ── 삭제된 함수: captureForCurrency() ───────────────────────────────────────
//
//    // ── 지폐 인식 (색상 기반) ─────────────────────────────────────────
//
//    private fun captureForCurrency() {
//        val file = File.createTempFile("vg_curr_", ".jpg", cacheDir)
//        imageCapture?.takePicture(
//            ImageCapture.OutputFileOptions.Builder(file).build(), cameraExecutor,
//            object : ImageCapture.OnImageSavedCallback {
//                override fun onImageSaved(o: ImageCapture.OutputFileResults) {
//                    Thread {
//                        try {
//                            val bmp = android.graphics.BitmapFactory.decodeFile(file.absolutePath)
//                            val cx = bmp.width / 2; val cy = bmp.height / 2
//                            val size = minOf(bmp.width, bmp.height) / 4
//                            val pixels = IntArray(size * size)
//                            bmp.getPixels(pixels, 0, size, cx - size/2, cy - size/2, size, size)
//                            bmp.recycle()
//                            var rSum = 0f; var gSum = 0f; var bSum = 0f
//                            pixels.forEach { p ->
//                                rSum += ((p shr 16) and 0xFF)
//                                gSum += ((p shr 8)  and 0xFF)
//                                bSum += (p and 0xFF)
//                            }
//                            val n = pixels.size.toFloat()
//                            val r = rSum / n; val g = gSum / n; val b = bSum / n
//                            val sentence = when {
//                                r > 180 && g > 150 && b < 130 -> "50000원권 같아요."
//                                r > g * 1.3f && r > b * 1.5f -> "5000원권 같아요."
//                                g > b && g > r * 0.9f && r < 180 -> "10000원권 같아요."
//                                b > r && b > g -> "1000원권 같아요."
//                                else -> "지폐를 정확히 인식하지 못했어요. 카메라에 지폐를 가득 채워보세요."
//                            }
//                            runOnUiThread { speak(sentence) }
//                        } catch (_: Exception) { runOnUiThread { speak("지폐 인식에 실패했어요.") } }
//                        finally { file.delete() }
//                    }.start()
//                }
//                override fun onError(e: ImageCaptureException) { speak("사진을 찍지 못했어요.") }
//            })
//    }

// ── 삭제된 함수: setMedicationAlarm() ───────────────────────────────────────
//
//    // ── 약 복용 알림 ─────────────────────────────────────────────────
//
//    private fun setMedicationAlarm(hour: Int) {
//        medicationTimer?.cancel()
//        val now = java.util.Calendar.getInstance()
//        val target = java.util.Calendar.getInstance().apply {
//            set(java.util.Calendar.HOUR_OF_DAY, hour)
//            set(java.util.Calendar.MINUTE, 0)
//            set(java.util.Calendar.SECOND, 0)
//            if (before(now)) add(java.util.Calendar.DAY_OF_YEAR, 1)
//        }
//        val delayMs = target.timeInMillis - now.timeInMillis
//        speak("매일 ${hour}시에 약 복용 알림을 설정했어요.")
//        medicationTimer = java.util.Timer(true)
//        medicationTimer?.schedule(object : java.util.TimerTask() {
//            override fun run() {
//                runOnUiThread {
//                    speak("약 드실 시간이에요. ${hour}시 약 복용 알림이에요.")
//                    val vibrator = getSystemService(VIBRATOR_SERVICE) as android.os.Vibrator
//                    vibrator.vibrate(android.os.VibrationEffect.createWaveform(
//                        longArrayOf(0, 300, 200, 300), -1))
//                }
//            }
//        }, delayMs, 24 * 60 * 60 * 1000)
//    }

// ── 삭제된 함수: startGpsTracking() ─────────────────────────────────────────
//
//    // ── GPS 하차 알림 ────────────────────────────────────────────────
//
//    @Suppress("MissingPermission")
//    private fun startGpsTracking(enableArrivalAlert: Boolean = false) {
//        try {
//            Log.d(
//                "VG_GPS",
//                "start enableArrivalAlert=$enableArrivalAlert fine=${hasPerm(Manifest.permission.ACCESS_FINE_LOCATION)} coarse=${hasPerm(Manifest.permission.ACCESS_COARSE_LOCATION)} server=${getSavedServerUrl()}"
//            )
//            val providers = listOf(
//                android.location.LocationManager.GPS_PROVIDER,
//                android.location.LocationManager.NETWORK_PROVIDER
//            ).filter { provider ->
//                locationManager?.isProviderEnabled(provider) == true
//            }
//
//            providers.forEach { provider ->
//                locationManager?.requestLocationUpdates(
//                    provider,
//                    3000L, 0f, locationListener  // 0f: 이동 거리 무관하게 3초마다 갱신
//                )
//                Log.d("VG_GPS", "requestLocationUpdates provider=$provider")
//            }
//
//            val lastLoc = providers
//                .mapNotNull { provider -> locationManager?.getLastKnownLocation(provider) }
//                .maxByOrNull { it.time }
//
//            if (lastLoc != null) {
//                handleLocationForGps(lastLoc, "lastKnown", enableArrivalAlert)
//            } else {
//                Log.w("VG_GPS", "location not ready providers=$providers")
//                if (enableArrivalAlert) {
//                    speak("GPS 신호를 찾는 중이에요. 잠시 후 다시 시도해 주세요.")
//                }
//            }
//
//            fusedLocationClient.lastLocation
//                .addOnSuccessListener { loc ->
//                    if (loc != null) {
//                        handleLocationForGps(loc, "fusedLast", enableArrivalAlert)
//                    } else {
//                        Log.w("VG_GPS", "fused lastLocation is null")
//                    }
//                }
//                .addOnFailureListener { e ->
//                    Log.e("VG_GPS", "fused lastLocation failed", e)
//                }
//
//            val tokenSource = com.google.android.gms.tasks.CancellationTokenSource()
//            fusedLocationClient.getCurrentLocation(
//                com.google.android.gms.location.Priority.PRIORITY_HIGH_ACCURACY,
//                tokenSource.token
//            )
//                .addOnSuccessListener { loc ->
//                    if (loc != null) {
//                        handleLocationForGps(loc, "fusedCurrent", enableArrivalAlert)
//                    } else {
//                        Log.w("VG_GPS", "fused currentLocation is null")
//                    }
//                }
//                .addOnFailureListener { e ->
//                    Log.e("VG_GPS", "fused currentLocation failed", e)
//                }
//        } catch (e: Exception) {
//            Log.e("VG_GPS", "GPS start failed", e)
//            if (enableArrivalAlert) {
//                speak("GPS를 사용할 수 없어요.")
//            }
//        }
//    }

// ── 삭제된 함수: stopGpsTracking() ──────────────────────────────────────────
//
//    private fun stopGpsTracking() {
//        locationManager?.removeUpdates(locationListener)
//        targetBusStop = null
//    }

// ── 삭제된 함수: sendGpsHeartbeat() ─────────────────────────────────────────
// (/ gps API 전용 호출 — /detect 요청과 별개)
//
//    private fun sendGpsHeartbeat(source: String) {
//        if (!isAnalyzing.get()) return
//        if (currentLat == 0.0 && currentLng == 0.0) return
//
//        val now = System.currentTimeMillis()
//        if (now - lastGpsSentTime < GPS_SEND_INTERVAL_MS) return
//        lastGpsSentTime = now
//
//        val serverUrl = getSavedServerUrl().trimEnd('/')
//        if (serverUrl.isEmpty()) {
//            Log.d("VG_GPS", "skip heartbeat: server URL empty")
//            return
//        }
//
//        val lat = currentLat
//        val lng = currentLng
//        val deviceId = getDeviceSessionId()
//        val requestId = "gps-$now"
//        Thread {
//            try {
//                val body = okhttp3.FormBody.Builder()
//                    .add("wifi_ssid", getWifiSsid())
//                    .add("device_id", deviceId)
//                    .add("lat", lat.toString())
//                    .add("lng", lng.toString())
//                    .add("request_id", requestId)
//                    .build()
//                val response = httpClient.newCall(
//                    Request.Builder().url("$serverUrl/gps").post(body).build()
//                ).execute()
//                Log.d(
//                    "VG_GPS",
//                    "heartbeat source=$source session=$deviceId request_id=$requestId status=${response.code} lat=$lat lng=$lng"
//                )
//                response.close()
//            } catch (e: Exception) {
//                Log.e("VG_GPS", "heartbeat failed source=$source request_id=$requestId", e)
//            }
//        }.start()
//    }

// ── 삭제된 헬퍼 함수들 ───────────────────────────────────────────────────────
//
//    private fun updateCurrentLocation(loc: android.location.Location, source: String) {
//        currentLat = loc.latitude
//        currentLng = loc.longitude
//        Log.d(
//            "VG_GPS",
//            "source=$source provider=${loc.provider} lat=$currentLat lng=$currentLng accuracy=${loc.accuracy}"
//        )
//        sendGpsHeartbeat(source)
//    }
//
//    private fun handleLocationForGps(
//        loc: android.location.Location,
//        source: String,
//        enableArrivalAlert: Boolean = false
//    ) {
//        updateCurrentLocation(loc, source)
//        if (enableArrivalAlert && targetBusStop == null) {
//            targetBusStop = loc
//            speak("현재 위치를 하차 알림 기준 위치로 저장했어요.")
//        }
//    }
