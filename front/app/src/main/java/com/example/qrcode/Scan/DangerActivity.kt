package com.example.qrcode.Scan

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.example.qrcode.MainActivity
import com.example.qrcode.R

class DangerActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_danger)

        val url = intent.getStringExtra("scanned_url") ?: "URL 없음"
        findViewById<TextView>(R.id.tvDangerUrl).text = url
        val reason = intent.getStringExtra("reason") ?: "이유 없음"

        findViewById<TextView>(R.id.tvReason).text = "탐지 사유: $reason"
        findViewById<Button>(R.id.btnBack).setOnClickListener {
            startActivity(Intent(this, MainActivity::class.java))
            finish()
        }
    }
}
