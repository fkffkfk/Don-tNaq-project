package com.example.qrcode.Settings

import android.os.Bundle
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.view.isVisible
import androidx.core.view.marginBottom
import androidx.core.widget.NestedScrollView
import com.example.qrcode.R
import com.example.qrcode.databinding.ActivityFaqBinding


class FaqActivity : AppCompatActivity() {
    private lateinit var binding: ActivityFaqBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityFaqBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 항목 1 바인딩
        val container1 = findViewById<ViewGroup>(R.id.item1_container)
        val header1 = findViewById<ViewGroup>(R.id.item1_header)
        val chevron1 = findViewById<ImageView>(R.id.item1_chevron)
        val answer1 = findViewById<TextView>(R.id.item1_answer)
        val divider1 = findViewById<View>(R.id.item1_divider)


        setupToggle(binding.guideScroll, container1, header1, chevron1, answer1,divider1)

        // 항목 2 바인딩
        val container2 = findViewById<ViewGroup>(R.id.item2_container)
        val header2 = findViewById<ViewGroup>(R.id.item2_header)
        val chevron2 = findViewById<ImageView>(R.id.item2_chevron)
        val answer2 = findViewById<TextView>(R.id.item2_answer)
        val divider2 = findViewById<View>(R.id.item2_divider)
        setupToggle(binding.guideScroll, container2, header2, chevron2,divider2,answer2 )

        //항목 3 바인딩
        val container3 = findViewById<ViewGroup>(R.id.item3_container)
        val header3 = findViewById<ViewGroup>(R.id.item3_header)
        val chevron3 = findViewById<ImageView>(R.id.item3_chevron)
        val answer3 = findViewById<TextView>(R.id.item3_answer)
        val divider3 = findViewById<View>(R.id.item3_divider)
        setupToggle(binding.guideScroll, container3, header3, chevron3,divider3,answer3 )

        //항목 4 바인딩
        val container4 = findViewById<ViewGroup>(R.id.item4_container)
        val header4 = findViewById<ViewGroup>(R.id.item4_header)
        val chevron4 = findViewById<ImageView>(R.id.item4_chevron)
        val answer4 = findViewById<TextView>(R.id.item4_answer)
        val divider4 = findViewById<View>(R.id.item4_divider)
        setupToggle(binding.guideScroll, container4, header4, chevron4,divider4,answer4 )

    }

    private fun setupToggle(
        scroll: NestedScrollView,
        container: ViewGroup,
        header: ViewGroup,
        chevron: ImageView,
        answer: View,
        divider: View ?= null

    ) {
        // 초기 상태 동기화
        chevron.rotation = if (answer.isVisible) 180f else 0f
        divider?.isVisible = answer.isVisible

        header.setOnClickListener {
            val willShow = !answer.isVisible
            answer.isVisible = willShow
            divider?.isVisible = willShow   //  선도 함께 토글

            chevron.animate().rotation(if (willShow) 180f else 0f).setDuration(150).start()

            if (willShow) {
                container.post {
                    scroll.smoothScrollTo(0, container.bottom + container.marginBottom)
                }
            }
        }
    }
}