package com.example.qrcode.network.networkData

data class SignupRequest(
    val userName: String,
    val userPassword: String,
    val public_key: String,
    val email: String,
    val is_admin: Boolean = false
)

data class SignupResponse(
    val message: String? = null,
    val user_id: Long? = null,
    val resend_available: Boolean? = null,
    val dev_verify_url: String? = null,
    val error: String? = null
)

data class SendVerificationRequest(
    val email: String,
    val public_key: String? = null
)

data class VerifyStatusResponse(
    val verified: Boolean,
    val message: String? = null
)