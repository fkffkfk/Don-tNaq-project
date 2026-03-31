package com.example.qrcode.Scan

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.R
import com.example.qrcode.data.db.AppDatabase
import com.example.qrcode.data.db.ScannedUrl
import com.example.qrcode.network.RetrofitClient.api
import com.example.qrcode.network.networkData.ModelRequest
import com.example.qrcode.network.networkData.ScanRequest
import com.example.qrcode.network.networkData.SecureScanRequest
import com.google.mlkit.vision.barcode.BarcodeScanning
import com.google.mlkit.vision.common.InputImage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

@androidx.camera.core.ExperimentalGetImage
class ScanActivity : AppCompatActivity() {

    private lateinit var cameraExecutor: ExecutorService
    private val CAMERA_REQUEST_CODE = 100
    private var alreadyScanned = false // 중복 인식 방지
    // 상단에 한 번만
    private val TAG = "ScanDebug"


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_scan)

        // 권한 체크 및 요청
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA)
            != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.CAMERA),
                CAMERA_REQUEST_CODE
            )
        } else {
            startCamera()
        }
        cameraExecutor = Executors.newSingleThreadExecutor()
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<out String>,
        grantResults: IntArray
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == CAMERA_REQUEST_CODE && grantResults.isNotEmpty() &&
            grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            startCamera()
        } else {
            Toast.makeText(this, "카메라 권한이 필요합니다", Toast.LENGTH_SHORT).show()
            finish()
        }
    }

    private fun startCamera() {
        Log.d("ScanDebug", "startCamera() 호출됨")
        val cameraProviderFuture = ProcessCameraProvider.getInstance(this)
        cameraProviderFuture.addListener({
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(findViewById<PreviewView>(R.id.previewView).surfaceProvider)
            }

            val barcodeScanner = BarcodeScanning.getClient()
            val imageAnalyzer = ImageAnalysis.Builder().build().also {
                it.setAnalyzer(cameraExecutor) { imageProxy ->
                    val mediaImage = imageProxy.image
                    if (mediaImage != null && !alreadyScanned) {
                        val image = InputImage.fromMediaImage(
                            mediaImage,
                            imageProxy.imageInfo.rotationDegrees
                        )

                        barcodeScanner.process(image)
                            .addOnSuccessListener { barcodes ->
                                for (barcode in barcodes) {
                                    barcode.rawValue?.let { raw ->
                                        alreadyScanned = true
                                        Log.d("ScanDebug", "🟩 QR 인식 성공 → raw: $raw")

                                        // ✅ 사용자 ID 가져오기
                                        val prefs = getSharedPreferences("user", MODE_PRIVATE)
                                        val email = prefs.getString("email", "anonymous@example.com") ?: "anonymous@example.com"
                                        val userIdInt = prefs.getInt("user_id", -1)
                                        Log.d("ScanDebug", "✅ email=$email / userIdInt=$userIdInt")

                                        // ✅ DB 저장
                                        val db = AppDatabase.getInstance(this)
                                        val scanned = ScannedUrl(url = raw, email = email)
                                        CoroutineScope(Dispatchers.IO).launch {
                                            db.scannedUrlDao().insertUrl(scanned)
                                            Log.d("ScanDebug", "💾 Room 저장 완료: $raw")

                                            try {
                                                val isIntegrityQr = raw.startsWith("naqjima://verify?")
                                                Log.d("ScanDebug", "🔍 isIntegrityQr=$isIntegrityQr")

                                                val url: String
                                                var jsonObject: JSONObject? = null

                                                if (isIntegrityQr) {
                                                    try {
                                                        val uri = Uri.parse(raw)
                                                        val payloadEncoded = uri.getQueryParameter("payload")
                                                        Log.d("ScanDebug", "🧩 payloadEncoded=$payloadEncoded")

                                                        val decodedBytes = android.util.Base64.decode(payloadEncoded, android.util.Base64.URL_SAFE or android.util.Base64.NO_WRAP)
                                                        val decoded = String(decodedBytes, Charsets.UTF_8)
                                                        Log.d("ScanDebug", "📥 decoded JSON=$decoded")

                                                        jsonObject = JSONObject(decoded)
                                                        url = jsonObject.optString("url", "")
                                                        Log.d("ScanDebug", "🌐 parsed url=$url")

                                                    } catch (e: Exception) {
                                                        Log.e("ScanDebug", "❌ 무결성 QR 파싱 실패: ${e.message}", e)
                                                        withContext(Dispatchers.Main) {
                                                            Toast.makeText(this@ScanActivity, "무결성 QR 파싱 오류", Toast.LENGTH_SHORT).show()
                                                        }
                                                        return@launch
                                                    }
                                                } else {
                                                    url = raw
                                                    Log.d("ScanDebug", "🌐 일반 QR url=$url")
                                                }

                                                // ✅ /scans 공통 전송
                                                val scanRes = api.postScan(ScanRequest(userIdInt, url))
                                                val scanId = scanRes.body()?.scan_id ?: run {
                                                    Log.e("ScanDebug", "❌ scan_id 응답 없음")
                                                    return@launch
                                                }
                                                Log.d("ScanDebug", "📡 scan_id=$scanId")

                                                if (isIntegrityQr && jsonObject != null) {
                                                    val signature = jsonObject.optString("sig")
                                                    val qrUserId = jsonObject.optInt("uid")

                                                    val verifyRes = api.secureScan(
                                                        SecureScanRequest(url, signature, qrUserId, scanId)
                                                    )
                                                    when (verifyRes.code()) {
                                                        410 -> {
                                                            val rawErr = verifyRes.errorBody()?.string().orEmpty()
                                                            val reason = runCatching { org.json.JSONObject(rawErr).optString("reason") }
                                                                .getOrDefault("이 QR코드는 유효기간이 만료되었습니다.")

                                                            withContext(Dispatchers.Main) {
                                                                val intent = Intent(this@ScanActivity, ResultActivity::class.java).apply {
                                                                    putExtra("scanned_url", url)
                                                                    putExtra("expired", true)                 // ✅ 만료 플래그
                                                                    putExtra("expire_reason", reason)         // ✅ 만료 사유
                                                                    putExtra("signature", signature)          // (옵션) 디버그/표시용
                                                                    putExtra("user_id", qrUserId)             // (옵션) 디버그/표시용
                                                                }
                                                                startActivity(intent)
                                                                finish()
                                                            }
                                                            return@launch
                                                        }
                                                        401 -> {
                                                            val rawErr = verifyRes.errorBody()?.string().orEmpty()
                                                            val reason = runCatching { org.json.JSONObject(rawErr).optString("reason") }
                                                                .getOrDefault("서명 검증에 실패했습니다. 위조된 QR일 수 있습니다.")
                                                            withContext(Dispatchers.Main) {
                                                                Toast.makeText(this@ScanActivity, reason, Toast.LENGTH_LONG).show()
                                                                finish()
                                                            }
                                                            return@launch
                                                        }
                                                        422 -> {
                                                            val rawErr = verifyRes.errorBody()?.string().orEmpty()
                                                            val obj = runCatching { org.json.JSONObject(rawErr) }.getOrNull()
                                                            val prob = obj?.optDouble("probability", 0.0) ?: 0.0
                                                            val reason = obj?.optString("reason", "악성 URL로 분류되었습니다.") ?: "악성 URL로 분류되었습니다."
                                                            withContext(Dispatchers.Main) {
                                                                val intent = Intent(this@ScanActivity, DangerActivity::class.java).apply {
                                                                    putExtra("scanned_url", url)
                                                                    putExtra("probability", prob)
                                                                    putExtra("reason", reason)
                                                                }
                                                                startActivity(intent)
                                                                finish()
                                                            }
                                                            return@launch
                                                        }
                                                    }

                                                    val prediction = verifyRes.body()?.prediction ?: "benign"
                                                    Log.d("ScanDebug", "🔐 secureScan 결과: $prediction")

                                                    withContext(Dispatchers.Main) {
                                                        val intent = if (prediction == "malicious") {
                                                            Intent(this@ScanActivity, DangerActivity::class.java)
                                                        } else {
                                                            Intent(this@ScanActivity, ResultActivity::class.java)
                                                        }
                                                        intent.putExtra("scanned_url", url)
                                                        intent.putExtra("signature", signature)
                                                        intent.putExtra("user_id", qrUserId)
                                                        startActivity(intent)
                                                        finish()
                                                    }

                                                } else {
                                                    // 일반 QR: /model-results 호출
                                                    val modelRes = api.predictMalicious(ModelRequest(scanId))

                                                    if (modelRes.isSuccessful) {
                                                        val body = modelRes.body()
                                                        val prediction = body?.prediction?.lowercase() ?: "benign"   // 👈 문자열만 처리
                                                        val prob = body?.probability ?: 0.0
                                                        val reason = body?.reason.orEmpty()

                                                        Log.d("ScanDebug", "🧠 모델 예측 정상 응답: prediction=$prediction, prob=$prob, reason=$reason")

                                                        withContext(Dispatchers.Main) {
                                                            val intent = if (prediction == "malicious") {
                                                                Intent(this@ScanActivity, DangerActivity::class.java).apply {
                                                                    putExtra("scanned_url", url)
                                                                    putExtra("probability", prob)
                                                                    putExtra("reason", reason)  // 악성 사유 전달
                                                                }
                                                            } else {
                                                                Intent(this@ScanActivity, ResultActivity::class.java).apply {
                                                                    putExtra("scanned_url", url)
                                                                }
                                                            }
                                                            startActivity(intent); finish()
                                                        }
                                                    } else {
                                                    val code = modelRes.code()
                                                    val rawErr = modelRes.errorBody()?.string().orEmpty()

                                                    var prediction = "malicious" // 기본값
                                                    var prob = 0.0
                                                    var reason = ""

                                                    try {
                                                        val obj = org.json.JSONObject(rawErr)
                                                        prediction = obj.optString("prediction", "malicious").lowercase()
                                                        prob = obj.optDouble("probability", 0.0)
                                                        reason = obj.optString("reason", obj.optString("message", "")) // message도 같이 확인
                                                    } catch (_: Exception) {
                                                        Log.w("ScanDebug", "⚠️ 에러 바디 JSON 파싱 실패: $rawErr")
                                                    }

                                                    Log.d("ScanDebug", "🧠 모델 예측 에러 응답(code=$code): prediction=$prediction, prob=$prob, reason=$reason")
                                                        withContext(Dispatchers.Main) {
                                                            if (code == 422) {
                                                                startActivity(Intent(this@ScanActivity, DangerActivity::class.java).apply {
                                                                    putExtra("scanned_url", url)
                                                                    putExtra("probability", prob)
                                                                    putExtra("reason", reason.ifEmpty { "악성 URL로 분류되었습니다." })
                                                                })
                                                            } else {
                                                                Toast.makeText(
                                                                    this@ScanActivity,
                                                                    reason.ifEmpty { "QR 검사 중 오류가 발생했습니다. (코드 $code)" },
                                                                    Toast.LENGTH_LONG
                                                                ).show()
                                                            }
                                                            finish()
                                                        }

                                                }

                                            }

                                            } catch (e: Exception) {
                                                Log.e("ScanDebug", "❌ 처리 중 오류: ${e.message}", e)
                                                withContext(Dispatchers.Main) {
                                                    Toast.makeText(this@ScanActivity, "서버 연결 실패", Toast.LENGTH_SHORT).show()
                                                }
                                            }
                                        }

                                        return@addOnSuccessListener
                                    }
                                }
                            }
                            .addOnFailureListener { e ->
                                Log.e("ScanDebug", "QR 인식 실패: $e")
                            }
                            .addOnCompleteListener {
                                imageProxy.close()
                            }

                    } else {
                        imageProxy.close()
                    }
                }
            }

            val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA
            try {
                val cameraProvider = cameraProviderFuture.get()
                cameraProvider.unbindAll()
                cameraProvider.bindToLifecycle(this, cameraSelector, preview, imageAnalyzer)
            } catch (e: Exception) {
                Log.e("Scan", "카메라 바인딩 실패: $e")
            }
        }, ContextCompat.getMainExecutor(this))
    }

    override fun onDestroy() {
        super.onDestroy()
        cameraExecutor.shutdown()
    }
}
