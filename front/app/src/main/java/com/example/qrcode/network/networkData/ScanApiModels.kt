package com.example.qrcode.network.networkData

data class ScanRequest(
    val user_id: Int,
    val url: String
)

data class ScanResponse(
    val scan_id: Int
)

data class ScanResult(
    val scan_id: Int,
    val url: String,
    val timestamp: String,
    val result: String, // "malicious", "benign"
    val reason: String
)

data class ScanHistoryItem(
    val scan_id: Int,
    val url: String,
    val status: String,
    val scanned_at: String,
    val result: String?,         // 예측 안 됐을 수 있으므로 nullable
    val score: Float?,           // 예측 확률, nullable
    val predicted_at: String?    // 예측 시간, nullable
)

