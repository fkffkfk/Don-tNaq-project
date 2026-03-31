package com.example.qrcode

import android.content.Intent
import android.graphics.drawable.Drawable
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import androidx.vectordrawable.graphics.drawable.Animatable2Compat
import com.bumptech.glide.Glide
import com.bumptech.glide.load.resource.gif.GifDrawable
import com.bumptech.glide.request.target.CustomTarget
import com.example.qrcode.auth.AuthActivity

import com.bumptech.glide.request.transition.Transition

private var navigated = false
private val LOOP_COUNT = 3
class SplashActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_splash)
        val ivSplash = findViewById<ImageView>(R.id.ivSplash)

        // GIF만 재생
        Glide.with(this)
            .asGif()
            .load(R.drawable.eyes_splash)
            .into(object : CustomTarget<GifDrawable>() {
                override fun onResourceReady(
                    resource: GifDrawable,
                    transition: Transition<in GifDrawable>?
                ) {
                    // 루프 횟수 지정
                    resource.setLoopCount(LOOP_COUNT)
                    resource.registerAnimationCallback(object : Animatable2Compat.AnimationCallback() {
                        override fun onAnimationEnd(drawable: Drawable?) {
                            goNext()
                        }
                    })
                    ivSplash.setImageDrawable(resource)
                    resource.start()
                }

                override fun onLoadCleared(placeholder: Drawable?) {
                    // 필요 시 처리
                }

                override fun onLoadFailed(errorDrawable: Drawable?) {
                    super.onLoadFailed(errorDrawable)
                    goNext() // 실패해도 다음 화면으로 이동
                }
            })
    }

    private fun goNext() {
        if (navigated) return
        navigated = true
        val prefs = getSharedPreferences("user", MODE_PRIVATE)
        val auto = prefs.getBoolean("auto_login", false)
        val email = prefs.getString("email", null)

        if (auto && email != null) {
            startActivity(Intent(this, MainActivity::class.java))
        } else {
            startActivity(Intent(this, AuthActivity::class.java))
        }
        startActivity(Intent(this, AuthActivity::class.java))
        finish()
    }

}