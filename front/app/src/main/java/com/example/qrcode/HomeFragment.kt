package com.example.qrcode

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.ImageView
import android.widget.TextView
import androidx.annotation.OptIn
import androidx.camera.core.ExperimentalGetImage
import androidx.core.content.ContextCompat
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.Board.FavoriteBoardActivity
import com.example.qrcode.History.AllScanHistoryActivity
import com.example.qrcode.Scan.ScanActivity
import com.example.qrcode.Settings.AppIntroActivity
import com.example.qrcode.Settings.FaqActivity
import com.example.qrcode.Settings.IntegrityQrHistoryActivity
import com.example.qrcode.Settings.SettingsActivity
import com.example.qrcode.auth.AuthActivity
import com.example.qrcode.network.RetrofitClient
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.data.BarData
import com.github.mikephil.charting.data.BarDataSet
import com.github.mikephil.charting.data.BarEntry
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlin.math.roundToInt

class HomeFragment : Fragment() {

    @OptIn(ExperimentalGetImage::class)
    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View? {
        val view = inflater.inflate(R.layout.fragment_home, container, false)

        // 상단 사용자명 표시
        val tvUserTitle = view.findViewById<TextView>(R.id.tvUserTitleHome)
        val prefs = requireContext().getSharedPreferences("user", Context.MODE_PRIVATE)
        val raw = prefs.getString("username", prefs.getString("email", "게스트")) ?: "게스트"
        val display = raw.substringBefore('@').ifBlank { "게스트" }
        tvUserTitle.text = "${display}님"

        // 작은 로그아웃
        view.findViewById<View>(R.id.tvLogoutSmall).setOnClickListener {
            requireContext().getSharedPreferences("user", Context.MODE_PRIVATE)
                .edit().clear().apply()

            startActivity(
                Intent(requireContext(), AuthActivity::class.java).apply {
                    flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
                }
            )
        }

        // 상단 카드 버튼
        view.findViewById<Button>(R.id.btnScanQr)?.setOnClickListener {
            startActivity(Intent(requireActivity(), ScanActivity::class.java))
        }
        view.findViewById<Button>(R.id.btnGenerateQr)?.setOnClickListener {
            startActivity(Intent(requireActivity(), IntegrityQrActivity::class.java))
        }

        // 하단 아이콘 네비게이션
        view.findViewById<ImageView>(R.id.infoImg)?.setOnClickListener {
            startActivity(Intent(requireActivity(), AppIntroActivity::class.java))
        }
        view.findViewById<ImageView>(R.id.settingsImg)?.setOnClickListener {
            startActivity(Intent(requireActivity(), SettingsActivity::class.java))
        }
        view.findViewById<ImageView>(R.id.recordImg)?.setOnClickListener {
            startActivity(Intent(requireActivity(), IntegrityQrHistoryActivity::class.java))
        }
        view.findViewById<ImageView>(R.id.faqImg)?.setOnClickListener {
            startActivity(Intent(requireActivity(), FaqActivity::class.java))
        }
        view.findViewById<ImageView>(R.id.favoriteImg)?.setOnClickListener {
            startActivity(Intent(requireActivity(), FavoriteBoardActivity::class.java))
        }


        // 버튼 이벤트
        val scanButton = view.findViewById<Button>(R.id.btnScanQr)
        scanButton.setOnClickListener {
            val intent = Intent(requireContext(), ScanActivity::class.java)
            startActivity(intent)
        }

        val generateButton = view.findViewById<Button>(R.id.btnGenerateQr)
        generateButton.setOnClickListener {
            val intent = Intent(requireContext(), IntegrityQrActivity::class.java)
            startActivity(intent)
        }

        // ✅ 요약 차트 초기화
        val chart = view.findViewById<BarChart>(R.id.summaryBarChart)

        lifecycleScope.launch {
            loadAndRenderSummary(chart)
        }

        return view
    }

    /** 서버에서 global / personal 데이터 불러와서 차트에 출력 */
    private suspend fun loadAndRenderSummary(chart: BarChart) {
        try {
            val globalRes = withContext(Dispatchers.IO) {
                RetrofitClient.api.getWeeks(count = 1, scope = "global", user_id = null)
            }
            val personalRes = withContext(Dispatchers.IO) {
                RetrofitClient.api.getWeeks(count = 1, scope = "personal", user_id = currentUserId())
            }

            if (globalRes.isSuccessful && personalRes.isSuccessful) {
                val globalWeek = globalRes.body()?.weeks?.firstOrNull()
                val personalWeek = personalRes.body()?.weeks?.firstOrNull()

                val globalMalicious = globalWeek?.scans?.malicious ?: 0
                val globalUsers = globalWeek?.uniqueUsers ?: 1
                val avg = (globalMalicious.toDouble() / globalUsers).roundToInt()

                val myCount = personalWeek?.scans?.malicious ?: 0
                Log.d("SummaryDebug", "avg=$avg, myCount=$myCount")
                Log.d("SummaryDebug", "globalRes=${globalRes.body()}")
                Log.d("SummaryDebug", "personalRes=${personalRes.body()}")

                withContext(Dispatchers.Main) {
                    renderChart(chart, avg, myCount)
                }
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    /** BarChart 그리기 */
    private fun renderChart(chart: BarChart, avg: Int, myCount: Int) {
        val entries = arrayListOf(
            BarEntry(0f, avg.toFloat()),
            BarEntry(1f, myCount.toFloat())
        )

        val set = BarDataSet(entries, "").apply {
            setDrawValues(true)
            valueTextSize = 14f
            colors = listOf(
                ContextCompat.getColor(requireContext(), R.color.gray), // 전체 평균
                ContextCompat.getColor(requireContext(), R.color.graph_purple)        // 내 기록
            )
            valueTextColor = ContextCompat.getColor(requireContext(), R.color.black)
        }

        val data = BarData(set).apply {
            barWidth = 0.4f
            setDrawValues(false) }
        chart.data = data
        chart.renderer = RoundedBarChartRenderer(chart, chart.animator, chart.viewPortHandler, 20f)
        chart.notifyDataSetChanged()

        chart.xAxis.apply {
            valueFormatter = IndexAxisValueFormatter(listOf("전체 평균", "내 악성 수"))
            granularity = 1f
            position = XAxis.XAxisPosition.BOTTOM
            setDrawGridLines(false)
            textSize = 12f
            yOffset = 10f
            chart.xAxis.textColor = ContextCompat.getColor(requireContext(), R.color.black)
        }
        chart.setExtraBottomOffset(10f)
        chart.axisLeft.isEnabled = false
        chart.axisRight.isEnabled = false
        chart.description.isEnabled = false
        chart.legend.isEnabled = false
        chart.setTouchEnabled(false)


        chart.invalidate()
        chart.animateY(700)
    }

    private fun currentUserId(): Int {
        val prefs = requireContext().getSharedPreferences("user", Context.MODE_PRIVATE)
        return prefs.getInt("user_id", -1)  // 저장된 값 없으면 -1
    }


}
