package com.example.qrcode.network.networkData

data class SecureQrRequest(
    val user_id: Int,
    val original_url: String,
    val signature: String,
    val qr_image_path: String,
    val validity: String
)

//검증 요청용 body
data class SecureScanRequest(
    val url: String,
    val signature: String,
    val user_id: Int,
    val scan_id: Int? = null
)

data class SecureScanResult(
    val message: String,
    val prediction: Int,
    val probability: Double,
    val scan_id: Int,
    val creator: String?,
)

data class SecureQrLog(
    val id: Int,
    val original_url: String,
    val signature: String,
    val qr_image_path: String,
    val created_at: String,
    val expires_at: String? = null
)