package com.example.qrcode.Settings

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.core.content.ContextCompat
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.qrcode.R
import com.example.qrcode.network.networkData.SecureQrLog
import java.io.File
import java.text.SimpleDateFormat
import java.util.*

class IntegrityQrAdapter(private val items: List<SecureQrLog>) :
    RecyclerView.Adapter<IntegrityQrAdapter.SecureQrViewHolder>() {

    inner class SecureQrViewHolder(v: View) : RecyclerView.ViewHolder(v) {

        val dueDate: TextView = v.findViewById(R.id.dueDate)
        val tvCreatedAt: TextView = v.findViewById(R.id.tvCreatedAt)
        val tvUrl: TextView = v.findViewById(R.id.tvUrl)
        val imgQrSmall: ImageView = v.findViewById(R.id.imgQrSmall)
        val imgQrLarge: ImageView = v.findViewById(R.id.imgQrLarge)
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): SecureQrViewHolder {
        val v = LayoutInflater.from(parent.context).inflate(R.layout.item_secure_qr, parent, false)
        return SecureQrViewHolder(v)
    }

    override fun onBindViewHolder(holder: SecureQrViewHolder, position: Int) {
        val item = items[position]
        val ctx = holder.itemView.context
        holder.tvCreatedAt.text = formatDate(item.created_at)
        holder.tvUrl.text = item.original_url
        if (!item.expires_at.isNullOrBlank()) {
            val isExpired = checkExpired(item.expires_at)
            holder.dueDate.text = if (isExpired) {
                "유효기간 만료"
            } else {
                formatDate(item.expires_at)
            }
            holder.dueDate.setTextColor(
                if (isExpired)
                    ContextCompat.getColor(ctx, android.R.color.darker_gray)
                else
                    ContextCompat.getColor(ctx, R.color.colorPrimary)
            )

        } else {
            holder.dueDate.text = "없음"
        }


        // ✅ URL만으로 키 생성
        val key = md5(item.original_url)
        val localFile = File(ctx.filesDir, "secure_qr/$key.png")

        // 로컬 색 PNG가 있으면 우선 사용, 없으면 서버 경로
        val loadTarget: Any = if (localFile.exists()) localFile else item.qr_image_path

        Glide.with(ctx).load(loadTarget)
            .placeholder(R.drawable.ic_qr_placeholder)
            .into(holder.imgQrSmall)

        Glide.with(ctx).load(loadTarget)
            .placeholder(R.drawable.ic_qr_placeholder)
            .into(holder.imgQrLarge)

        holder.itemView.setOnClickListener {
            holder.imgQrLarge.visibility =
                if (holder.imgQrLarge.visibility == View.GONE) View.VISIBLE else View.GONE
        }
    }

    private fun checkExpired(expiresAt: String): Boolean {
        return try {
            val parser = SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.ENGLISH)
            parser.timeZone = TimeZone.getTimeZone("UTC")
            val date = parser.parse(expiresAt)
            if (date != null) {
                val now = Date()
                now.after(date)   // ✅ 현재 시간이 만료일보다 뒤면 true
            } else false
        } catch (e: Exception) {
            false
        }
    }


    private fun md5(s: String): String {
        val md = java.security.MessageDigest.getInstance("MD5")
        return md.digest(s.toByteArray()).joinToString("") { "%02x".format(it) }
    }


    private fun formatDate(raw: String): String = try {
        val parser = SimpleDateFormat("EEE, dd MMM yyyy HH:mm:ss z", Locale.ENGLISH).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        val date = parser.parse(raw)
        val formatter = SimpleDateFormat("yyyy-MM-dd HH:mm", Locale.ENGLISH).apply {
            timeZone = TimeZone.getTimeZone("UTC")
        }
        date?.let { formatter.format(it) } ?: raw
    } catch (e: Exception) { raw }

    override fun getItemCount(): Int = items.size
}
