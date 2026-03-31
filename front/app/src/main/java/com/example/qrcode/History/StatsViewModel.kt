package com.example.qrcode.History

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.qrcode.data.db.StatsRepository
import com.example.qrcode.network.networkData.WeeklyStatsResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class StatsViewModel(private val repo: StatsRepository) : ViewModel() {
    enum class Scope { GLOBAL, ME }

    private val _data = MutableStateFlow<WeeklyStatsResponse?>(null)
    val data: StateFlow<WeeklyStatsResponse?> = _data
    val loading = MutableStateFlow(false)
    val error = MutableStateFlow<String?>(null)

    fun load(
        weeksBack: Int = 0,
        includeHidden: Int = 0,
        scope: Scope = Scope.GLOBAL,
        userId: Int? = null
    ) = viewModelScope.launch {
        loading.value = true; error.value = null
        try {
            val scopeStr = if (scope == Scope.ME) "personal" else "global"  // 서버 스펙
            val uid = if (scope == Scope.ME) userId else null               // GLOBAL이면 null
            val res = repo.weekly(weeksBack, includeHidden, scopeStr, uid)
            if (res.isSuccessful) _data.value = res.body()
            else error.value = "서버 오류: ${res.code()}"
        } catch (e: Exception) { error.value = e.message }
        finally { loading.value = false }
    }
}




