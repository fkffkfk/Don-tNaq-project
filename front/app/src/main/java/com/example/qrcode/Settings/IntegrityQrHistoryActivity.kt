package com.example.qrcode.Settings

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import androidx.recyclerview.widget.RecyclerView
import com.example.qrcode.R
import com.example.qrcode.network.RetrofitClient
import kotlinx.coroutines.launch

class IntegrityQrHistoryActivity : AppCompatActivity() {

    private lateinit var recyclerView: RecyclerView
    private lateinit var adapter: IntegrityQrAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_integrity_qr_history)

        recyclerView = findViewById(R.id.recyclerSecureQr)
        recyclerView.layoutManager = LinearLayoutManager(this)

        lifecycleScope.launch {
            val prefs = getSharedPreferences("user", MODE_PRIVATE)
            val userId = prefs.getInt("user_id", -1)
            val resp = RetrofitClient.api.listSecureQrLogs(userId)
            if (resp.isSuccessful) {
                val logs = resp.body() ?: emptyList()
                adapter = IntegrityQrAdapter(logs)
                recyclerView.adapter = adapter
            } else {
                Toast.makeText(this@IntegrityQrHistoryActivity, "불러오기 실패", Toast.LENGTH_SHORT).show()
            }
        }
    }
}
