package com.example.qrcode.Settings

import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import com.example.qrcode.R
import com.example.qrcode.databinding.ActivityAppGuideBinding

class AppGuideActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAppGuideBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAppGuideBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val scroll = binding.root

        // 1
        setupToggle(
            scroll,
            findViewById(R.id.q1_container),
            findViewById(R.id.q1_header),
            findViewById(R.id.q1_chevron),
            findViewById(R.id.q1_answer),
            findViewById(R.id.q1_divider)
        )

        // 2
        setupToggle(
            scroll,
            findViewById(R.id.q2_container),
            findViewById(R.id.q2_header),
            findViewById(R.id.q2_chevron),
            findViewById(R.id.q2_answer),
            findViewById(R.id.q2_divider)
        )

        // 3
        setupToggle(
            scroll,
            findViewById(R.id.q3_container),
            findViewById(R.id.q3_header),
            findViewById(R.id.q3_chevron),
            findViewById(R.id.q3_answer),
            findViewById(R.id.q3_divider)
        )

        // 4
        setupToggle(
            scroll,
            findViewById(R.id.q4_container),
            findViewById(R.id.q4_header),
            findViewById(R.id.q4_chevron),
            findViewById(R.id.q4_answer),
            findViewById(R.id.q4_divider)
        )

        // 5
        setupToggle(
            scroll,
            findViewById(R.id.q5_container),
            findViewById(R.id.q5_header),
            findViewById(R.id.q5_chevron),
            findViewById(R.id.q5_answer),
            findViewById(R.id.q5_divider)
        )

        // 6
        setupToggle(
            scroll,
            findViewById(R.id.q6_container),
            findViewById(R.id.q6_header),
            findViewById(R.id.q6_chevron),
            findViewById(R.id.q6_answer),
            findViewById(R.id.q6_divider)
        )
    }

    private fun setupToggle(
        scroll: View,
        container: ViewGroup,
        header: ViewGroup,
        chevron: ImageView,
        answer: View,
        divider: View? = null
    ) {
        chevron.rotation = if (answer.isVisible) 180f else 0f
        divider?.isVisible = answer.isVisible

        header.setOnClickListener {
            val willShow = !answer.isVisible
            answer.isVisible = willShow
            divider?.isVisible = willShow

            chevron.animate()
                .rotation(if (willShow) 180f else 0f)
                .setDuration(150).start()
        }
    }
}

