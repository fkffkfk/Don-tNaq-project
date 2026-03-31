package com.example.qrcode.data.db

import com.example.qrcode.network.ApiService
import com.example.qrcode.network.networkData.WeeklyStatsResponse
import retrofit2.Response

class StatsRepository(private val api: ApiService) {
    suspend fun weekly(
        weeksBack: Int = 0,
        includeHidden: Int = 0,
        scope: String = "global",
        userId: Int? = null
    ): Response<WeeklyStatsResponse> {
        return api.getWeeklyStats(weeksBack, includeHidden, scope, userId)
    }
}


