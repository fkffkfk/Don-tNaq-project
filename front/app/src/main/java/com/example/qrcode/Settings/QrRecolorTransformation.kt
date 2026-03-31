package com.example.qrcode.Settings

import android.graphics.Bitmap
import android.graphics.Color
import com.bumptech.glide.load.engine.bitmap_recycle.BitmapPool
import com.bumptech.glide.load.resource.bitmap.BitmapTransformation
import java.security.MessageDigest

class QrRecolorTransformation(
    private val targetColor: Int,
    private val threshold: Int = 40 // 어두움 임계값(0~255)
) : BitmapTransformation() {

    override fun updateDiskCacheKey(md: MessageDigest) {
        md.update(("QrRecolorTransformation:$targetColor:$threshold").toByteArray())
    }

    override fun transform(
        pool: BitmapPool,
        toTransform: Bitmap,
        outWidth: Int,
        outHeight: Int
    ): Bitmap {
        val src = if (toTransform.config == Bitmap.Config.ARGB_8888)
            toTransform
        else
            toTransform.copy(Bitmap.Config.ARGB_8888, true)

        val w = src.width
        val h = src.height
        val out = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)

        val pixels = IntArray(w * h)
        src.getPixels(pixels, 0, w, 0, 0, w, h)

        val tr = Color.red(targetColor)
        val tg = Color.green(targetColor)
        val tb = Color.blue(targetColor)

        for (i in pixels.indices) {
            val c = pixels[i]
            val a = Color.alpha(c)
            val r = Color.red(c)
            val g = Color.green(c)
            val b = Color.blue(c)

            // r,g,b 모두 threshold 이하 → "검정"으로 간주하여 치환
            pixels[i] = if (r <= threshold && g <= threshold && b <= threshold && a > 0)
                Color.argb(255, tr, tg, tb)
            else
                Color.argb(a, r, g, b)
        }

        out.setPixels(pixels, 0, w, 0, 0, w, h)
        return out
    }
}
