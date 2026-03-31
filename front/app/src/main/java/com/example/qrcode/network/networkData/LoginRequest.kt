package com.example.qrcode.network.networkData

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val email: String,
    @SerializedName("userPassword") val password: String
)
