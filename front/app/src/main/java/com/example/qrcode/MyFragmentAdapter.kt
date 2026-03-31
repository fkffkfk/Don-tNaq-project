package com.example.qrcode

import androidx.fragment.app.Fragment
import androidx.fragment.app.FragmentActivity
import androidx.viewpager2.adapter.FragmentStateAdapter
import com.example.qrcode.Board.BoardFragment
import com.example.qrcode.History.HistoryFragment

class MyFragmentAdapter(activity: FragmentActivity) : FragmentStateAdapter(activity) {
    override fun getItemCount(): Int = 3 // 탭 수

    override fun createFragment(position: Int): Fragment {
        return when (position) {
            0 -> HomeFragment()
            1 -> BoardFragment()
            else -> HistoryFragment()
        }
    }
}
