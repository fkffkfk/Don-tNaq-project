package com.example.qrcode.network.networkData

// WeeklyDayStat.kt
data class WeeklyDayStat(
    val index: Int,
    val day: String,
    val date: String,
    val malicious_count: Int,
    val unique_user_count: Int
)

// WeeklyStatsSummary.kt
data class WeeklyStatsSummary(
    val total_malicious: Int,
    val unique_users_in_range: Int
)

// WeeklyStatsResponse.kt
data class WeeklyStatsResponse(
    val week_start: String,
    val week_end: String,
    val weeks_back: Int,
    val include_hidden: Boolean,
    val summary: WeeklyStatsSummary,
    val days: List<WeeklyDayStat>
)
