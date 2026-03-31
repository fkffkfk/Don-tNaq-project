package com.example.qrcode.History

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.TextView
import androidx.recyclerview.widget.RecyclerView
import com.example.qrcode.R
import com.example.qrcode.network.networkData.ScanHistoryItem
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.TimeZone

class AllScanHistoryAdapter :
    RecyclerView.Adapter<AllScanHistoryAdapter.ViewHolder>() {

    private var items: List<ScanHistoryItem> = listOf()

    fun submitList(data: List<ScanHistoryItem>) {
        items = data
        notifyDataSetChanged()
    }

    class ViewHolder(view: View) : RecyclerView.ViewHolder(view) {
        val tvUrl: TextView = view.findViewById(R.id.tvUrl)
        val tvDate: TextView = view.findViewById(R.id.tvDate)
        val tvResult: TextView = view.findViewById(R.id.tvResult)     // 예측 결과
        val tvScore: TextView = view.findViewById(R.id.tvScore)       // 예측 확률
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): ViewHolder {
        val view = LayoutInflater.from(parent.context)
            .inflate(R.layout.item_scanned_url, parent, false)
        return ViewHolder(view)
    }

    override fun getItemCount(): Int = items.size

    override fun onBindViewHolder(holder: ViewHolder, position: Int) {
        val item = items[position]
        holder.tvUrl.text = item.url
        holder.tvDate.text = formatDate(item.scanned_at)

        // ✅ 예측 결과 표시
        holder.tvResult.text = when (item.result) {
            "1" -> "악성"
            else -> "정상"
        }

        // ✅ 확률은 퍼센트로 변환
        holder.tvScore.text = item.score?.let { "${(it * 100).toInt()}%" } ?: "-"
    }

    private fun formatDate(dateStr: String?): String {
        if (dateStr.isNullOrBlank()) return "-"
        return try {
            val utc = TimeZone.getTimeZone("UTC")

            val inputFormats = listOf(
                // Thu, 09 Oct 2025 21:34:45 GMT  → 문자열의 타임존(z)을 존중해 파싱
                SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.ENGLISH),

                // 2025-10-09T21:34:45 → 오프셋이 없으니 UTC로 가정
                SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US).apply {
                    timeZone = utc
                },

                // 2025-10-09 21:34:45 → 오프셋이 없으니 UTC로 가정
                SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).apply {
                    timeZone = utc
                }
            )

            val outputFormat = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.US).apply {
                timeZone = utc // ← 항상 UTC로 출력
            }

            var parsed: Date? = null
            for (fmt in inputFormats) {
                try {
                    parsed = fmt.parse(dateStr)
                    if (parsed != null) break
                } catch (_: Exception) {}
            }

            parsed?.let { outputFormat.format(it) } ?: dateStr
        } catch (_: Exception) {
            dateStr ?: "-"
        }
    }





}

