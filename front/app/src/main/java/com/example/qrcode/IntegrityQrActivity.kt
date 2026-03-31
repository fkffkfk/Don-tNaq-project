package com.example.qrcode

import android.content.res.ColorStateList
import android.graphics.Bitmap
import android.graphics.Color
import android.os.Bundle
import android.util.Base64
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.widget.ImageViewCompat
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.databinding.ActivityIntegrityQrBinding
import com.example.qrcode.network.RetrofitClient
import com.example.qrcode.network.networkData.*
import com.google.zxing.BarcodeFormat
import com.google.zxing.qrcode.QRCodeWriter
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.security.KeyStore
import java.security.MessageDigest
import java.security.Signature

private val TAG = "IntegrityQrActivity"
class IntegrityQrActivity : AppCompatActivity() {

    private lateinit var binding: ActivityIntegrityQrBinding
    private var generatedQr: Bitmap? = null
    private var lastQrText: String? = null
    private var selectedColor: Int = Color.BLACK
    private var lastOriginalUrl: String? = null        // 서버/목록에 보이는 original_url



    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityIntegrityQrBinding.inflate(layoutInflater)
        setContentView(binding.root)
        // 0) 팔레트는 시작 시 숨김 (XML에서 gone이면 생략 가능)
        binding.colorPalette.visibility = View.GONE
        // 1) 팔레트 클릭 리스너: 생성된 QR만 재색칠
        val pick: (Int) -> Unit = let@{ color ->
            selectedColor = color
            if (lastQrText == null) {
                Toast.makeText(this, "먼저 QR을 생성하세요.", Toast.LENGTH_SHORT).show()
                return@let
            }
            recolorGeneratedQr()
        }
        binding.colorBlack.setOnClickListener { pick(Color.BLACK) }
        binding.colorMalcha.setOnClickListener  { pick(Color.parseColor("#4B5E4A")) }
        binding.colorBlue.setOnClickListener   { pick(Color.parseColor("#031888")) }
        binding.colorSkyBlue.setOnClickListener { pick(Color.parseColor("#6096FD")) }
        binding.colorMint.setOnClickListener{ pick(Color.parseColor("#48C5D1")) }
        binding.colorPink.setOnClickListener{ pick(Color.parseColor("#FB788E")) }
        binding.colorOrange.setOnClickListener  { pick(Color.parseColor("#FAA788")) }
        binding.colorBeige.setOnClickListener  { pick(Color.parseColor("#CCAA88")) }



        binding.btnGenerate.setOnClickListener {
            lifecycleScope.launch {
                val rawUrl = binding.editUrl.text.toString().trim()
                if (rawUrl.isBlank()) { toast("URL을 입력하세요."); return@launch }

                // (선택) URL 정규화: 마지막 슬래시 제거
                val url = if (rawUrl.endsWith("/")) rawUrl.dropLast(1) else rawUrl
                Log.d(TAG, "입력 URL(raw): $rawUrl")
                Log.d(TAG, "정규화 URL(norm): $url")

                //이미 생성된 url인지 확인
                val key = md5(url)
                val file = File(filesDir, "secure_qr/$key.png")
                if (file.exists()) {
                    toast("이미 QR코드가 생성된 URL입니다.")
                    return@launch
                }

                val userId = getUserIdFromPrefs()
                Log.d(TAG, "userId(from prefs): $userId")
                if (userId == -1) { toast("로그인이 필요합니다."); return@launch }

                val api = RetrofitClient.api

                try {
                    // 1) /scans
                    Log.d(TAG, "📡 POST /scans body = {user_id=$userId, url=$url}")
                    val scanRes = api.postScan(ScanRequest(userId, url))
                    Log.d(TAG, "⬅️ /scans status=${scanRes.code()} msg=${scanRes.message()}")
                    if (!scanRes.isSuccessful) { toast("스캔 실패"); return@launch }
                    val scanId = scanRes.body()?.scan_id ?: run { toast("scan_id 없음"); return@launch }
                    Log.d(TAG, "✅ scan_id=$scanId")

                    // 2) /model-results
                    Log.d(TAG, "📡 POST /model-results body = {scan_id=$scanId}")
                    val predRes = api.predictMalicious(ModelRequest(scanId))
                    Log.d(TAG, "⬅️ /model-results status=${predRes.code()} msg=${predRes.message()}")
                    val prediction = predRes.body()?.prediction
                    Log.d(TAG, "✅ 모델 예측 결과: $prediction")
                    if (prediction == null) { toast("예측 실패"); return@launch }
                    if (prediction == "malicious") { toast("악성 URL. 생성 중단."); return@launch }

                    // 3) ECDSA 서명 (url + userId)
                    val messageToSign = url + userId
                    val msgBytes = messageToSign.toByteArray(Charsets.UTF_8)
                    val msgHash = MessageDigest.getInstance("SHA-256").digest(msgBytes)
                    val msgHashB64 = Base64.encodeToString(msgHash, Base64.NO_WRAP)
                    Log.d(TAG, "서명메시지(messageToSign)='$messageToSign'")
                    Log.d(TAG, "서명메시지 길이=${messageToSign.length}, SHA256(Base64)=$msgHashB64")
                    val email = getEmailFromPrefs()
                    val alias = aliasFromEmail(email)
                    Log.d(TAG, "Keystore alias=$alias, email=$email")
                    val signature = signDataWithKeystore(messageToSign, alias)
                    Log.d(TAG, "서명(base64) len=${signature.length}, head=${signature.take(12)}...")

                    // 5) QR 텍스트 만들고 이미지 생성/저장
                    val qrPayloadJson = JSONObject().apply {
                        put("uid", userId)
                        put("url", url)
                        put("sig", signature)
                    }.toString()

                    val payloadEncoded = Base64.encodeToString(
                        qrPayloadJson.toByteArray(Charsets.UTF_8),
                        Base64.URL_SAFE or Base64.NO_WRAP
                    )
                    val qrText = "naqjima://verify?payload=$payloadEncoded"
                    lastQrText = qrText

                    Log.d(TAG, "QR JSON len=${qrText.length}, head=${qrText.take(60)}...")
                    // QR 생성 시 선택된 색상 적용
                    val qrBitmap = generateQrCode(
                        data = qrText,
                        foreground = selectedColor,   // 전경만 선택색
                        background = Color.WHITE      // 배경은 고정 흰색
                    )
                    generatedQr = qrBitmap
                    binding.imageQr.setImageTintList(null) // tint 안 씀
                    binding.imageQr.setImageBitmap(qrBitmap)

                    binding.colorPalette.visibility = View.VISIBLE
                    binding.btnQrSave.visibility = View.VISIBLE

                    val file = File(getExternalFilesDir(null), "qr_${System.currentTimeMillis()}.png")
                    FileOutputStream(file).use { out -> qrBitmap.compress(Bitmap.CompressFormat.PNG, 100, out) }
                    Log.d(TAG, "QR 저장 경로: ${file.absolutePath}")

                    // 6) 생성 로그 저장: /secure-qr
                    val selectedValidity = when (binding.radioValidityGroup.checkedRadioButtonId) {
                        R.id.radio1day -> "1day"
                        R.id.radio7days -> "7days"
                        R.id.radio30days -> "30days"
                        R.id.radio90days -> "90days"
                        R.id.radio150days -> "150days"
                        else -> "7days" // 기본값
                    }

                    val logBody = SecureQrRequest(
                        user_id = userId, original_url = url, signature = signature,
                        qr_image_path = file.absolutePath, validity = selectedValidity
                    )
                    Log.d(TAG, "📡 POST /secure-qr body = $logBody")

                    val saveRes = api.saveSecureQr(logBody)
                    if (!saveRes.isSuccessful) {
                        toast("로그 저장 실패(${saveRes.code()})"); return@launch
                    }
                    lastOriginalUrl = url
                    Log.d(TAG, "saved.original_url=${lastOriginalUrl}")

                    Log.d(TAG, "⬅️ /secure-qr status=${saveRes.code()} msg=${saveRes.message()}")
                    if (!saveRes.isSuccessful) { toast("로그 저장 실패(${saveRes.code()})"); return@launch }
                    if (lastOriginalUrl != null ) {
                        saveColoredQrToAppStorage(
                            bmp = qrBitmap,
                            originalUrl = lastOriginalUrl!!
                        )
                    }
                    toast("url 검사완료!")

                } catch (e: Exception) {
                    Log.e(TAG, "예외: ${e.message}", e)
                    toast("오류: ${e.message}")
                }
            }
        }

        binding.btnQrSave.setOnClickListener {
            val qrText = lastQrText ?: return@setOnClickListener toast("먼저 QR을 생성하세요.")
            val bmpToSave = generateQrCode(data = qrText, foreground = selectedColor, background = Color.WHITE)
            generatedQr = bmpToSave
            binding.imageQr.setImageBitmap(bmpToSave)

            // ✅ 내부 저장도 같은 키로 다시 한번 저장 (덮어쓰기 OK)
            saveColoredQrToAppStorage(
                bmp = bmpToSave,
                originalUrl = lastOriginalUrl ?: binding.editUrl.text.toString()
            )

            val ok = saveBitmapToGallery(bmpToSave, "secure_qr_${System.currentTimeMillis()}.png")
            Toast.makeText(this, if (ok) "인증 qr 저장완료!" else "저장 실패", Toast.LENGTH_SHORT).show()
        }

    }
    private fun md5(input: String): String {
        val md = java.security.MessageDigest.getInstance("MD5")
        return md.digest(input.toByteArray()).joinToString("") { "%02x".format(it) }
    }

    // 색 입힌 비트맵을 앱 내부 저장소에 저장 (URL만 키로 사용)
    private fun saveColoredQrToAppStorage(
        bmp: Bitmap,
        originalUrl: String
    ): File {
        val key = md5(originalUrl)                
        val dir = File(filesDir, "secure_qr")
        if (!dir.exists()) dir.mkdirs()
        val outFile = File(dir, "$key.png")
        FileOutputStream(outFile).use { fos ->
            bmp.compress(Bitmap.CompressFormat.PNG, 100, fos)
        }
        return outFile
    }

    private fun nowRfc1123Utc(): String {
        val f = java.text.SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", java.util.Locale.ENGLISH)
        f.timeZone = java.util.TimeZone.getTimeZone("UTC")
        return f.format(java.util.Date())
    }


    private fun toast(msg: String) = Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()

    private fun getUserIdFromPrefs(): Int {
        val prefs = getSharedPreferences("user", MODE_PRIVATE)
        return prefs.getInt("user_id", -1)
    }
    private fun getEmailFromPrefs(): String {
        val prefs = getSharedPreferences("user", MODE_PRIVATE)
        return (prefs.getString("email", "") ?: "").trim().lowercase()
    }
    // Keystore alias에 쓸 수 있도록 email 정규화
    private fun aliasFromEmail(email: String): String {
        val safe = email.replace(Regex("[^a-z0-9._-]"), "_")
        return "key_$safe"
    }

    private fun signDataWithKeystore(data: String, alias: String): String {
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }

        val entry = keyStore.getEntry(alias, null) as? KeyStore.PrivateKeyEntry
            ?: throw IllegalStateException("Keystore에서 키를 찾을 수 없습니다: $alias")

        val signature = Signature.getInstance("SHA256withECDSA")
        signature.initSign(entry.privateKey)
        signature.update(data.toByteArray(Charsets.UTF_8))

        val signedBytes = signature.sign()
        return Base64.encodeToString(signedBytes, Base64.NO_WRAP)
    }

    private fun generateQrCode(
        data: String,
        size: Int = 512,
        foreground: Int = Color.BLACK,
        background: Int = Color.WHITE
    ): Bitmap {
        val bits = QRCodeWriter().encode(data, BarcodeFormat.QR_CODE, size, size)
        val bmp = Bitmap.createBitmap(size, size, Bitmap.Config.RGB_565)
        for (x in 0 until size) {
            for (y in 0 until size) {
                bmp.setPixel(x, y, if (bits[x, y]) foreground else background)
            }
        }
        return bmp
    }

    private fun recolorGeneratedQr() {
        val qrText = lastQrText ?: return
        val recolored = generateQrCode(
            data = qrText,
            foreground = selectedColor,
            background = Color.WHITE
        )
        binding.imageQr.setImageTintList(null)
        binding.imageQr.setImageBitmap(recolored)
        generatedQr = recolored
    }

    //qr이미지 갤러리 저장 함수
    fun saveBitmapToGallery(bitmap: Bitmap, fileName: String): Boolean {
        return try {
            if (android.os.Build.VERSION.SDK_INT >= 29) {
                // Android 10+ : MediaStore 사용
                val values = android.content.ContentValues().apply {
                    put(android.provider.MediaStore.Images.Media.DISPLAY_NAME, fileName)
                    put(android.provider.MediaStore.Images.Media.MIME_TYPE, "image/png")
                    put(android.provider.MediaStore.Images.Media.RELATIVE_PATH, "Pictures/QRcode")
                    put(android.provider.MediaStore.Images.Media.IS_PENDING, 1)
                }
                val uri = contentResolver.insert(
                    android.provider.MediaStore.Images.Media.EXTERNAL_CONTENT_URI, values
                ) ?: return false

                contentResolver.openOutputStream(uri)?.use { out ->
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
                } ?: return false

                values.clear()
                values.put(android.provider.MediaStore.Images.Media.IS_PENDING, 0)
                contentResolver.update(uri, values, null, null)
                true
            } else {
                // Android 9 이하: 공용 Pictures/QRcode에 파일 저장 후 스캔
                val dir = android.os.Environment
                    .getExternalStoragePublicDirectory(android.os.Environment.DIRECTORY_PICTURES)
                val appDir = java.io.File(dir, "QRcode").apply { if (!exists()) mkdirs() }
                val file = java.io.File(appDir, fileName)
                java.io.FileOutputStream(file).use { out ->
                    bitmap.compress(Bitmap.CompressFormat.PNG, 100, out)
                }
                android.media.MediaScannerConnection.scanFile(
                    this, arrayOf(file.absolutePath), arrayOf("image/png"), null
                )
                true
            }
        } catch (e: Exception) {
            Log.e(TAG, "갤러리 저장 오류: ${e.message}", e)
            false
        }
    }

}
