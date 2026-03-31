package com.example.qrcode.History

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.RadioGroup
import androidx.fragment.app.Fragment
import androidx.fragment.app.viewModels
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.R
import com.example.qrcode.data.db.StatsRepository
import com.example.qrcode.network.RetrofitClient
import com.example.qrcode.network.networkData.WeeklyDayStat
import com.github.mikephil.charting.charts.BarChart
import com.github.mikephil.charting.data.BarData
import com.github.mikephil.charting.data.BarDataSet
import com.github.mikephil.charting.data.BarEntry

import com.google.android.material.button.MaterialButton
import kotlinx.coroutines.flow.collectLatest
import android.widget.TextView
import android.widget.AdapterView
import android.widget.ArrayAdapter
import android.widget.Spinner
import androidx.core.content.ContextCompat
import com.github.mikephil.charting.components.YAxis
import com.example.qrcode.History.HighlightedXAxisRenderer
import com.example.qrcode.RoundedBarChartRenderer
import com.github.mikephil.charting.formatter.DefaultValueFormatter
import com.github.mikephil.charting.formatter.IndexAxisValueFormatter
import com.github.mikephil.charting.formatter.ValueFormatter


class HistoryFragment : Fragment() {

    private val TAG = "HistoryFragment"

    private var weekItemsDesc: List<com.example.qrcode.network.networkData.WeekItem> = emptyList()

    private val viewModel: StatsViewModel by viewModels {
        val api = RetrofitClient.api
        val repo = StatsRepository(api)
        object : ViewModelProvider.Factory {
            override fun <T : ViewModel> create(c: Class<T>): T = StatsViewModel(repo) as T
        }
    }

    private var scope: StatsViewModel.Scope = StatsViewModel.Scope.GLOBAL
    private var viewMode: Mode = Mode.COUNT

    private enum class Mode { COUNT, UNIQUE }

    private val DOW_KO = listOf("월", "화", "수", "목", "금", "토", "일")
    private var selectedWeeksBack: Int = 0

    private fun currentUserId(): Int {
        val prefs =
            requireContext().getSharedPreferences("user", android.content.Context.MODE_PRIVATE)
        val id = prefs.getInt("user_id", -1)
        Log.d(TAG, "prefs(user).all=${prefs.all} / picked id=$id")
        return id
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View = inflater.inflate(R.layout.fragment_history, container, false)

    override fun onViewCreated(v: View, s: Bundle?) {
        Log.d(TAG, "onViewCreated()")

        val tvError: TextView? = v.findViewById(R.id.tvError)
        val barChart = v.findViewById<BarChart>(R.id.barChart)
        val scopeGroup = v.findViewById<RadioGroup>(R.id.scopeGroup)

        // 주차 선택 UI
        val weekSpinner = v.findViewById<Spinner>(R.id.weekSpinner)
        val tvWeekRange = v.findViewById<TextView>(R.id.tvWeekRange)
        reloadWeeks(weekSpinner, tvWeekRange)

        // QR스캔기록 버튼
        v.findViewById<MaterialButton>(R.id.btnAllHistory).setOnClickListener {
            startActivity(Intent(requireContext(), AllScanHistoryActivity::class.java))
        }

        // 전체/내 통계 스코프 전환
        scopeGroup.setOnCheckedChangeListener { _, checkedId ->
            scope =
                if (checkedId == R.id.rbMe) StatsViewModel.Scope.ME else StatsViewModel.Scope.GLOBAL
            val uid = currentUserId().takeIf { scope == StatsViewModel.Scope.ME && it > 0 }
            reloadWeeks(weekSpinner, tvWeekRange)
        }
        scopeGroup.check(R.id.rbGlobal)

        // 2) 선택 시 weeksBack = position (0부터 시작)
        weekSpinner.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(
                parent: AdapterView<*>,
                view: View?,
                position: Int,
                id: Long
            ) {
                selectedWeeksBack = position   // 0=이번주, 1=저번주...

                // ▶ 빠진 중괄호 보충
                weekItemsDesc.getOrNull(position)?.let {
                    tvWeekRange.text = "${it.start} ~ ${it.end}"
                }

                val uid = currentUserId().takeIf { scope == StatsViewModel.Scope.ME && it > 0 }
                viewModel.load(
                    weeksBack = selectedWeeksBack,
                    includeHidden = 0,
                    scope = scope,
                    userId = uid
                )
            }

            override fun onNothingSelected(parent: AdapterView<*>) {}
        }


        // 수집부
        viewLifecycleOwner.lifecycleScope.launchWhenStarted {
            viewModel.loading.collectLatest { Log.d(TAG, "loading=$it") }
        }
        viewLifecycleOwner.lifecycleScope.launchWhenStarted {
            viewModel.error.collectLatest { err ->
                if (err != null) Log.e(TAG, "에러: $err")
            }
        }
        viewLifecycleOwner.lifecycleScope.launchWhenStarted {
            viewModel.data.collectLatest { resp ->
                Log.d(
                    TAG,
                    "resp: ${resp?.week_start}~${resp?.week_end}, days=${resp?.days?.size ?: 0}"
                )
                val start = resp?.week_start.orEmpty()
                val end = resp?.week_end.orEmpty()
                tvWeekRange.text =
                    if (start.isNotBlank() && end.isNotBlank()) "$start ~ $end" else ""
                renderBarChart(barChart, resp?.days)
            }
        }

        // 3) 초기값: 1주차(=이번주)
        val uid = currentUserId().takeIf { scope == StatsViewModel.Scope.ME && it > 0 }
    }

    // 차트 렌더 (클래스 스코프에 두기! 로컬 함수 X)
    // 차트 렌더
    private fun renderBarChart(chart: BarChart, days: List<WeeklyDayStat>?) {
        try {
            val byIndex = (days ?: emptyList()).associateBy { it.index }
            val ordered = (0..6).map { i ->
                byIndex[i] ?: WeeklyDayStat(
                    index = i,
                    day = DOW_KO[i],
                    date = "",
                    malicious_count = 0,
                    unique_user_count = 0
                )
            }

            val entries = ordered.mapIndexed { idx, d ->
                val y = if (viewMode == Mode.COUNT) d.malicious_count else d.unique_user_count
                BarEntry(idx.toFloat(), y.toFloat())
            }

            val title = if (viewMode == Mode.COUNT) "요일별 악성 건수" else "요일별 고유 사용자 수"
            val set = BarDataSet(entries, title).apply {
                setDrawValues(true) //막대 위에 값 표시
                valueTextSize = 12f //값 글씨 크기 조절
                // 오늘 요일 index (0=월, ..., 6=일)
                val todayIndex =
                    java.util.Calendar.getInstance().get(java.util.Calendar.DAY_OF_WEEK) - 2
                val fixedTodayIndex = if (todayIndex < 0) 6 else todayIndex

                // ✅ Bar 색상
                val colors = entries.mapIndexed { idx, _ ->
                    if (idx == fixedTodayIndex) {
                        ContextCompat.getColor(requireContext(), R.color.graph_purple)  // 오늘: 진한색
                    } else {
                        ContextCompat.getColor(requireContext(), R.color.gray) // 나머지: 연한색
                    }
                }
                this.colors = colors
            }


            // ✅ X축 라벨 포맷터 (오늘만 강조)
            val todayIndex = java.util.Calendar.getInstance().get(java.util.Calendar.DAY_OF_WEEK) - 2
            val fixedTodayIndex = if (todayIndex < 0) 6 else todayIndex
            chart.axisRight.isEnabled = false

            val yL = chart.axisLeft
            yL.axisMinimum = 0f        // 0부터 시작 (바닥 붙이기의 핵심)
            yL.spaceBottom = 0f
            chart.highlightValues(null)
            chart.clear()

// 1) 데이터 설정
            val data = BarData(set).apply {
                barWidth = 0.6f // 선택사항
            }
            chart.data = data
            chart.renderer = RoundedBarChartRenderer(
                chart = chart,
                animator = chart.animator,
                viewPortHandler = chart.viewPortHandler,
                radiusDp = 12f // dp 단위로 구현돼 있다면 그대로
            )
// 1) 라벨을 위로, 반드시 setData/renderer 이후에
            chart.setDrawValueAboveBar(true)

// 2) 전체 데이터셋에 값 표시 켜기 + 글씨 크기/색
            chart.data.apply {
                setDrawValues(true)         // 전역 on
                setValueTextSize(12f)
                setValueTextColor(android.graphics.Color.BLACK) // 막대/배경과 대비되는 색
                setValueFormatter(object : com.github.mikephil.charting.formatter.ValueFormatter() {
                    // MPAndroidChart 버전 호환: 둘 다 넣어두면 안전
                    override fun getBarLabel(e: com.github.mikephil.charting.data.BarEntry): String =
                        e.y.toInt().toString()

                    override fun getFormattedValue(
                        value: Float
                    ): String = value.toInt().toString()
                })
            }

// 3) 꼭! 버퍼 초기화 → 갱신 → 그리기 (라벨이 사라지는 주 원인)
            chart.setDrawValueAboveBar(false)


// 데이터셋 가져오기 (0번 세트 가정)
            val ds = chart.data.getDataSetByIndex(0) as BarDataSet
// 2) 라벨을 막대 안쪽에 강제로 표시 (바깥으로 빼고 싶으면 true)
            chart.setDrawValueAboveBar(false)

// 3) 값 라벨 켜기 + "TEST" 강제
            ds.setDrawValues(true)
            ds.valueTextSize = 18f
            ds.valueTextColor = android.graphics.Color.WHITE


// 4) 보이기 방해 요소 제거
            chart.setMaxVisibleValueCount(Int.MAX_VALUE)
            chart.axisLeft.axisMinimum = 0f
            chart.axisLeft.spaceTop = 0f
            chart.axisLeft.spaceBottom = 0f
            chart.axisRight.isEnabled = false
            chart.setExtraOffsets(0f, 0f, 0f, 0f)

// 5) 갱신
            chart.data.notifyDataChanged()
            chart.renderer.initBuffers()
            chart.notifyDataSetChanged()
            chart.invalidate()

            val zeroHidingFormatter = object : ValueFormatter() {
                override fun getBarLabel(e: BarEntry): String {
                    return if (e.y <= 0f) "" else e.y.toInt().toString()
                }
                override fun getFormattedValue(value: Float): String {
                    return if (value <= 0f) "" else value.toInt().toString()
                }
            }
            ds.valueFormatter = zeroHidingFormatter
            // 올바른 코드
            chart.setXAxisRenderer(
                HighlightedXAxisRenderer(
                    chart.viewPortHandler,
                    chart.xAxis,
                    chart.getTransformer(YAxis.AxisDependency.LEFT),
                    fixedTodayIndex,
                    ContextCompat.getColor(requireContext(), R.color.gray),
                    ContextCompat.getColor(requireContext(), R.color.graph_purple)
                )
            )
            // ✅ X축 (요일 표시)
            chart.xAxis.apply {
                valueFormatter = IndexAxisValueFormatter(DOW_KO)
                granularity = 1f
                position = com.github.mikephil.charting.components.XAxis.XAxisPosition.BOTTOM
                setDrawGridLines(false) // X축 세로 보조선 제거
                textSize = 18f
                yOffset = 10f
            }
            // ✅ Y축 제거
            chart.axisLeft.isEnabled = false   // 왼쪽 Y축 제거
            chart.axisRight.isEnabled = false  // 오른쪽 Y축 제거
            // ✅ 불필요한 description 제거
            chart.description.isEnabled = false
            chart.legend.isEnabled = false     // 범례(오른쪽 아래 "요일별 악성 건수") 제거
            chart.setNoDataText("")
            chart.invalidate()

        } catch (e: Exception) {
            Log.e(TAG, "renderBarChart() 오류: ${e.message}", e)
        }
        chart.setExtraBottomOffset(12f)
    }
    private fun reloadWeeks(weekSpinner: Spinner, tvWeekRange: TextView) {
        viewLifecycleOwner.lifecycleScope.launchWhenStarted {
            val scopeStr = if (scope == StatsViewModel.Scope.ME) "personal" else "global"
            val uidOpt = currentUserId().takeIf { scope == StatsViewModel.Scope.ME && it > 0 }

            // ① /stats/weeks 호출
            val weeksRes = RetrofitClient.api.getWeeks(
                count = 8,
                include_hidden = 0,
                scope = scopeStr,
                user_id = uidOpt
            )

            if (!weeksRes.isSuccessful) {
                Log.e(TAG, "/stats/weeks 실패: ${weeksRes.code()}")
                return@launchWhenStarted
            }

            // ② 과거→최근(ASC) → 최근→과거로 역전 (1주차=이번주)
            val weeksAsc = weeksRes.body()?.weeks ?: emptyList()
            weekItemsDesc = weeksAsc.asReversed()

            // ③ 스피너 채우기 (라벨은 1주차~N주차)
            val labels = weekItemsDesc.indices.map { i ->
                if (i == 0) {
                    "이번주"
                } else {
                    "${i}주전"
                }
            }

            weekSpinner.adapter = ArrayAdapter(
                requireContext(),
                android.R.layout.simple_spinner_dropdown_item,
                labels
            )

            // ④ 기본 선택: 1주차(=이번주)
            selectedWeeksBack = 0
            weekSpinner.setSelection(0, false)

            // ⑤ 기간 텍스트 갱신
            weekItemsDesc.getOrNull(0)?.let { tvWeekRange.text = "${it.start} ~ ${it.end}" }

            // ⑥ 첫 데이터 로드 (weeks_back=0)
            val uid = currentUserId().takeIf { scope == StatsViewModel.Scope.ME && it > 0 }
            viewModel.load(weeksBack = 0, includeHidden = 0, scope = scope, userId = uid)
        }
    }

}
