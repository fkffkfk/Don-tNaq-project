package com.example.qrcode.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "scanned_urls")
data class ScannedUrl(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val url: String,
    //userid연결해서 해당id가 뭘 스캔했는지 저장ㅡ
    val email:String,
    val timestamp: Long = System.currentTimeMillis()
)
