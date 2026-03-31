package com.example.qrcode.network.networkData
data class WithdrawRequest(
    val email: String,
    val password: String,
    val mode: String = "soft" // 기본은 soft ,hard로 변경은 가능함
)
data class WithdrawResponse(val message: String)
