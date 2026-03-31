package com.example.qrcode.History

import android.content.Context
import android.os.Bundle
import android.util.Log
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.qrcode.databinding.ActivityAllScanHistoryBinding
import com.example.qrcode.network.RetrofitClient
import kotlinx.coroutines.launch

class AllScanHistoryActivity : AppCompatActivity() {

    private lateinit var binding: ActivityAllScanHistoryBinding
    private lateinit var adapter: AllScanHistoryAdapter

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAllScanHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = AllScanHistoryAdapter()
        binding.recyclerView.layoutManager = LinearLayoutManager(this)
        binding.recyclerView.adapter = adapter

        val prefs = getSharedPreferences("user", Context.MODE_PRIVATE)

        lifecycleScope.launch {
            val userId = getSharedPreferences("user", MODE_PRIVATE).getInt("user_id", -1)
            if (userId == -1) return@launch

            val response = RetrofitClient.api.getUserScanHistory(userId)
            if (response.isSuccessful) {
                val historyList = response.body() ?: emptyList()
                adapter.submitList(historyList)
                Log.d("ScanHistory", "조회된 스캔기록: ${historyList.size}")
            } else {
                Log.e("ScanHistory", "서버 응답 실패: ${response.code()}")
            }
        }

    }
}
