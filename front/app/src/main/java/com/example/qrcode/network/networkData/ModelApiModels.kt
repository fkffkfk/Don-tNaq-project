package com.example.qrcode.network.networkData

data class ModelRequest(
    val scan_id: Int
)
data class ModelResponse(
    val message: String?,
    val scan_id: Int?,
    val prediction: String?,
    val probability: Float,
    val reason: String?
)
