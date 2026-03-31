package com.example.qrcode.network.networkData

data class WeeksResponse(val weeks: List<WeekItem>)

data class WeekItem(
    val weekNo: Int,
    val start: String,  // "YYYY-MM-DD"
    val end: String,
    val label: String,  // "1주차 (08.19~08.25)" 같은 문자열
    val scans: Scans,
    val uniqueUsers: Int
)

data class Scans(
    val total: Int,
    val benign: Int,
    val malicious: Int
)