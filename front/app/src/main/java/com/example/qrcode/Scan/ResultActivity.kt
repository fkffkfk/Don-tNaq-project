package com.example.qrcode.Scan

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.bumptech.glide.Glide
import com.example.qrcode.MainActivity
import com.example.qrcode.R
import com.example.qrcode.network.RetrofitClient.api
import com.example.qrcode.network.networkData.SecureScanRequest
import kotlinx.coroutines.*
import org.jsoup.Jsoup

class ResultActivity : AppCompatActivity() {
    private val scope = CoroutineScope(Dispatchers.Main)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_result)

        val url = intent.getStringExtra("scanned_url") ?: return
        val signature = intent.getStringExtra("signature")
        val userId = intent.getIntExtra("user_id", -1)


        val tvUrl = findViewById<TextView>(R.id.tvScannedUrl)
        tvUrl.text = url

        val linkURL = findViewById<TextView>(R.id.btnURL)
        linkURL.setOnClickListener {
            val intent = Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url))
            startActivity(intent)
        }
        val btnURL = findViewById<Button>(R.id.btnURL)
        val URL = findViewById<TextView>(R.id.tvScannedUrl)
        val tvTitle = findViewById<TextView>(R.id.tvTitle)
        val tvDesc = findViewById<TextView>(R.id.tvDescription)
        val ivThumbnail = findViewById<ImageView>(R.id.ivThumbnail)
        val picWarn = findViewById<ImageView>(R.id.pic_warn)
        val tvCreator = findViewById<TextView>(R.id.maded) //생성한사람 안보이고 보이게하는역할
        val isExpired = intent.getBooleanExtra("expired", false)
        if (isExpired) {
            val expireReason = intent.getStringExtra("expire_reason")
                ?: "이 QR코드는 유효기간이 만료되었습니다."

            // 미리보기 로딩/서버 재검증 생략하고 즉시 안내
            tvTitle.text = "만료된 인증 QR입니다"
            tvDesc.text = expireReason
            tvCreator.visibility = View.VISIBLE
            tvCreator.text = "QR 생성자: (생성자 정보 없음)"
            picWarn.visibility = View.VISIBLE

            // 필요하면 썸네일 영역 가림
            ivThumbnail.visibility = View.GONE
            btnURL.visibility = View.GONE
            URL.visibility = View.GONE

            // 링크 버튼은 그대로 두되, 열기 원치 않으면 아래 한 줄로 비활성화 가능
            // linkURL.isEnabled = false

            // 홈 버튼, 링크 버튼 리스너는 기존 그대로 유지
            linkURL.setOnClickListener {
                startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
            }

            findViewById<Button>(R.id.btnHome).setOnClickListener {
                startActivity(Intent(this, MainActivity::class.java).apply { putExtra("goToTab", 0) })
                finish()
            }
            return
        }
        scope.launch {
            val previewData = withContext(Dispatchers.IO) { fetchMetaInfo(url) }
            previewData?.let {
                tvTitle.text = it.title
                tvDesc.text = it.description
                Glide.with(this@ResultActivity).load(it.image).into(ivThumbnail)
            }
        }

        // 🔹 1) 무결성 QR일 경우 → 서버에 검증 요청
        if (signature != null && userId != -1) {
            scope.launch {
                try {
                    val resp = api.secureScan(
                        SecureScanRequest(url, signature, userId, null)
                    )
                    if (resp.isSuccessful) {
                        val body = resp.body()
                        if (body != null && body.prediction == 0) {
                            val creator = body.creator ?: "알 수 없음"
                            tvCreator.visibility = View.VISIBLE
                            tvCreator.text = "QR 생성자: $creator"
                        }
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        } else {
            // 일반 QR일 경우 → creator는 숨김
            tvCreator.visibility = View.GONE
            scope.launch {
                try {
                    val scanId = intent.getIntExtra("scan_id", -1)
                    if (scanId != -1) {
                        val resp = api.getModelResult(mapOf("scan_id" to scanId))
                        if (resp.isSuccessful) {
                            val body = resp.body()
                            if (body != null && body.prediction == "malicious") {
                                val intent = Intent(this@ResultActivity, DangerActivity::class.java).apply {
                                    putExtra("scanned_url", url)
                                    putExtra("reason", body.reason ?: "사유 없음")
                                    putExtra("probability", body.probability)
                                }
                                startActivity(intent)
                                finish()
                            }
                        } else {
                            // 서버 응답 실패 로그
                            println("🚫 서버 응답 실패: ${resp.code()}")
                        }
                    }
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }


        //홈버튼
        findViewById<Button>(R.id.btnHome).setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java).apply {
                putExtra("goToTab", 0)
            })
            finish()
        }
    }

    data class LinkPreview(val title: String, val description: String, val image: String?)

    private fun fetchMetaInfo(url: String): LinkPreview? {
        return try {
            val doc = Jsoup.connect(url).get()
            val title = doc.select("meta[property=og:title]").attr("content")
                .ifBlank { doc.title() }
            val desc = doc.select("meta[property=og:description]").attr("content")
            val image = doc.select("meta[property=og:image]").attr("content")
            LinkPreview(title, desc, image)
        } catch (e: Exception) {
            e.printStackTrace()
            null
        }
    }
}