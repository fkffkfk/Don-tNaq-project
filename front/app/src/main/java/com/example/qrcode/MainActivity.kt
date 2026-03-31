package com.example.qrcode



import android.os.Bundle
import android.widget.ImageView
import android.widget.TextView

import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.core.content.ContextCompat
import androidx.core.view.GravityCompat
import com.example.qrcode.databinding.ActivityMainBinding
import com.google.android.material.tabs.TabLayoutMediator


class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // 다크 모드
        val prefssss = getSharedPreferences("user", MODE_PRIVATE)
        val isDark = prefssss.getBoolean("dark_mode", false)
        AppCompatDelegate.setDefaultNightMode(
            if (isDark) AppCompatDelegate.MODE_NIGHT_YES
            else AppCompatDelegate.MODE_NIGHT_NO
        )



        // ViewPager + Tab 연결
        val tabTitles = listOf("홈", "게시판", "통계")
        val tabIcons = listOf(R.drawable.home, R.drawable.board, R.drawable.stats)


        binding.viewPager.adapter = MyFragmentAdapter(this)

        TabLayoutMediator(binding.tabLayout, binding.viewPager) { tab, pos ->
            val v = layoutInflater.inflate(R.layout.item_tab_icon_text, null)
            v.findViewById<ImageView>(R.id.tIcon).setImageResource(tabIcons[pos])
            v.findViewById<TextView>(R.id.tText).text = tabTitles[pos]
            tab.customView = v
        }.attach()
        //입체감 보존용
        binding.tabLayout.tabIconTint = null
        for (i in 0 until binding.tabLayout.tabCount) {
            binding.tabLayout.getTabAt(i)?.icon?.setTintList(null)   // 혹시 남아있을 tint 제거
        }

        // 인디케이터(밑줄) 완전 제거 — 버전 상관없이 동작
        binding.tabLayout.apply {
            setSelectedTabIndicator(null)                 // 인디케이터 drawable 자체 제거
            setSelectedTabIndicatorColor(android.graphics.Color.TRANSPARENT) // 혹시 모를 색도 무력화
            //tabRippleColor = null                         // 눌렀을 때 물결 효과도 끔(원치 않으면 주석)
        }

        // ✅ 특정 탭으로 이동
        val goToTab = intent.getIntExtra("goToTab", -1)
        if (goToTab in 0..2) {
            binding.viewPager.currentItem = goToTab
        }


    }


    override fun onBackPressed() {
        if (binding.drawerLayout.isDrawerOpen(GravityCompat.START)) {
            binding.drawerLayout.closeDrawer(GravityCompat.START)
        } else {
            super.onBackPressed()
        }
    }


}


