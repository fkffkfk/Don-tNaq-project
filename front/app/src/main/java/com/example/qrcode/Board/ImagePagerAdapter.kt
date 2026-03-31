// ImagePagerAdapter.kt
package com.example.qrcode.Board

import android.graphics.drawable.Drawable
import android.net.Uri
import android.util.Log
import android.view.ViewGroup
import android.widget.ImageView
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.bumptech.glide.load.DataSource
import com.bumptech.glide.load.engine.GlideException
import com.bumptech.glide.request.RequestListener


import com.bumptech.glide.request.target.Target
import java.io.File

class ImagePagerAdapter(
    private val items: List<String>
) : RecyclerView.Adapter<ImagePagerAdapter.VH>() {

    inner class VH(val image: ImageView) : RecyclerView.ViewHolder(image)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val iv = ImageView(parent.context).apply {
            layoutParams = RecyclerView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            scaleType = ImageView.ScaleType.CENTER_CROP
            adjustViewBounds = true
        }
        return VH(iv)
    }


    override fun onBindViewHolder(holder: VH, position: Int) {
        val src = items[position].trim()

        val model: Any = when {
            src.startsWith("http://", true) || src.startsWith("https://", true) -> src
            src.startsWith("content://", true) || src.startsWith("file://", true) -> Uri.parse(src)
            else -> File(src)
        }

        Glide.with(holder.image.context)
            .load(model)
            .fitCenter()
            .error(android.R.drawable.ic_menu_report_image)
            .listener(debugLogListener(src))
            .into(holder.image)
    }


    private fun debugLogListener(src: String): RequestListener<Drawable> {
        return object : RequestListener<Drawable> {
            override fun onLoadFailed(
                e: GlideException?,
                model: Any?,
                target: Target<Drawable>,
                isFirstResource: Boolean
            ): Boolean {
                Log.e("Glide", "❌ Load fail: $src", e)
                return false // false 로 해야 error() placeholder 표시
            }

            override fun onResourceReady(
                resource: Drawable,
                model: Any,
                target: Target<Drawable>?,
                dataSource: DataSource,
                isFirstResource: Boolean
            ): Boolean {
                Log.d("Glide", "✅ Load success: $src (from $dataSource)")
                return false
            }

        }
    }


    override fun getItemCount(): Int = items.size
}
