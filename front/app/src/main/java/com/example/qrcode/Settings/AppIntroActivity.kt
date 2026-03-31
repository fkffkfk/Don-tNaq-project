package com.example.qrcode.Settings

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.example.qrcode.databinding.ActivityAppIntroBinding

class AppIntroActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAppIntroBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAppIntroBinding.inflate(layoutInflater)
        setContentView(binding.root)


    }
}