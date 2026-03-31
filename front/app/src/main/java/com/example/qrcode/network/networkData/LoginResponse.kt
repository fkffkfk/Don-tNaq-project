package com.example.qrcode.network.networkData

import com.google.gson.annotations.SerializedName

data class LoginResponse(
    //val success: Boolean,
    val message: String,
    @SerializedName("user_id") val userId: Int?,
    @SerializedName("is_admin") val isAdmin: Boolean = false
)


