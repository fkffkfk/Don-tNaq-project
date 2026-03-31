package com.example.qrcode.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "users")
data class User(
    @PrimaryKey val email: String,
    val password: String,
    val displayName: String,
    val publicKey: String? = null,
    val is_verified: Boolean = false // 이메일 인증 관련
)