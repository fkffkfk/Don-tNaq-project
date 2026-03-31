package com.example.qrcode.Settings

import android.content.Intent
import android.content.SharedPreferences
import android.os.Bundle
import android.text.InputType
import android.util.Patterns
import android.view.MenuItem
import android.view.WindowManager
import android.view.inputmethod.EditorInfo
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.Switch
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate

import androidx.lifecycle.lifecycleScope
import com.example.qrcode.R
import com.example.qrcode.auth.AuthActivity
import com.example.qrcode.data.db.AppDatabase
import com.example.qrcode.network.RetrofitClient
import com.example.qrcode.network.networkData.WithdrawRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class SettingsActivity : AppCompatActivity() {
    private lateinit var prefs: SharedPreferences

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_settings)


        prefs = getSharedPreferences("user", MODE_PRIVATE)

        val switchAutoLogin: Switch = findViewById(R.id.switchAutoLogin)
        val switchDarkMode: Switch = findViewById(R.id.switchDarkMode)

        // 자동로그인
       switchAutoLogin.isChecked = prefs.getBoolean("auto_login", false)
        switchAutoLogin.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("auto_login", isChecked).apply()
        }

        // 다크모드
        val current = AppCompatDelegate.getDefaultNightMode()
        val isDark = when (current) {
            AppCompatDelegate.MODE_NIGHT_YES -> true
            AppCompatDelegate.MODE_NIGHT_NO -> false
            else -> prefs.getBoolean("dark_mode", false) // 시스템/따르기일 때는 저장값 사용
        }
        switchDarkMode.isChecked = isDark

        switchDarkMode.setOnCheckedChangeListener { _, isChecked ->
            prefs.edit().putBoolean("dark_mode", isChecked).apply()

            val desired = if (isChecked) AppCompatDelegate.MODE_NIGHT_YES else AppCompatDelegate.MODE_NIGHT_NO
            if (AppCompatDelegate.getDefaultNightMode() != desired) {
                AppCompatDelegate.setDefaultNightMode(desired)
            }
        }

        // "탈퇴하기" 버튼
        findViewById<TextView>(R.id.tvwithdraw).setOnClickListener {
            showWithdrawDialog()
        }
    }

    // 이메일(필요 시) + 비밀번호 입력 다이얼로그 (코드 생성)
    private fun showWithdrawDialog() {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            val pad = (16 * resources.displayMetrics.density).toInt()
            setPadding(pad, pad, pad, 0)
        }

        val tvInfo = TextView(this).apply {
            text = "탈퇴 시 계정은 익명화되며 일부 기록은 통계 보존 목적으로 남을 수 있습니다."
            val bottom = (8 * resources.displayMetrics.density).toInt()
            setPadding(0, 0, 0, bottom)
        }

        // 저장된 이메일(있으면 미리 넣어줌)
        val storedEmail = getStoredEmail()

        val edtEmail = EditText(this).apply {
            hint = "이메일"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS
            setText(storedEmail ?: "")
            // 저장된 이메일이 있으면 수정 안 하게 잠금(원하면 지워도 됨)
            isEnabled = storedEmail.isNullOrBlank()
        }

        val edtPw = EditText(this).apply {
            hint = "비밀번호"
            inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_VARIATION_PASSWORD
            imeOptions = EditorInfo.IME_ACTION_DONE
        }

        container.addView(
            tvInfo,
            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        )
        container.addView(
            edtEmail,
            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        )
        container.addView(
            edtPw,
            LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT)
        )

        val dialog = AlertDialog.Builder(this)
            .setTitle("회원 탈퇴")
            .setView(container)
            .setPositiveButton("탈퇴", null) // 버튼 클릭은 아래에서 직접 처리
            .setNegativeButton("취소", null)
            .create()

        dialog.setOnShowListener {
            // 키보드 자동 표시
            dialog.window?.setSoftInputMode(WindowManager.LayoutParams.SOFT_INPUT_STATE_VISIBLE)

            val ok = dialog.getButton(AlertDialog.BUTTON_POSITIVE)
            ok.setOnClickListener {
                val email = (edtEmail.text?.toString() ?: "").trim().lowercase()
                val pw = edtPw.text?.toString()?.trim().orEmpty()

                if (email.isBlank()) { edtEmail.error = "이메일을 입력하세요."; return@setOnClickListener }
                if (!Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                    edtEmail.error = "이메일 형식을 확인하세요."; return@setOnClickListener
                }
                if (pw.isEmpty()) { edtPw.error = "비밀번호를 입력하세요."; return@setOnClickListener }

                dialog.dismiss()
                performWithdraw(email, pw)
            }
        }

        edtPw.setOnEditorActionListener { _, actionId, _ ->
            if (actionId == EditorInfo.IME_ACTION_DONE) {
                dialog.getButton(AlertDialog.BUTTON_POSITIVE)?.performClick()
                true
            } else false
        }

        dialog.show()
    }

    // SharedPreferences에서 이메일 가져오기 (없으면 null)
    private fun getStoredEmail(): String? {
        getSharedPreferences("auth", MODE_PRIVATE).getString("email", null)?.let { return it }
        getSharedPreferences("email", MODE_PRIVATE).getString("email", null)?.let { return it }
        return null
    }

    private fun performWithdraw(email: String, password: String) {
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api.withdraw(WithdrawRequest(email, password))
                if (resp.isSuccessful) {
                    Toast.makeText(this@SettingsActivity, "탈퇴 완료", Toast.LENGTH_SHORT).show()

                    // 1) 세션(토큰 등) 정리
                    getSharedPreferences("user", MODE_PRIVATE).edit().clear().apply()

                    // 2) 환경설정 SharedPreferences 정리: 자동로그인 끄고, 로컬 이메일 흔적 제거(다크모드는 유지)
                    val ep = getSharedPreferences("user", MODE_PRIVATE).edit()
                    ep.putBoolean("auto_login", false)
                    ep.remove("email")
                    ep.apply()

                    // 3) 로컬 DB 초기화
                    withContext(Dispatchers.IO) {
                        AppDatabase.getInstance(this@SettingsActivity).clearAllTables()
                    }

                    // 4) 로그인 화면으로 이동
                    startActivity(
                        Intent(this@SettingsActivity, AuthActivity::class.java)
                            .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                    )
                } else {
                    val msg = resp.errorBody()?.string().orEmpty()
                    AlertDialog.Builder(this@SettingsActivity)
                        .setMessage(
                            Regex("\"error\"\\s*:\\s*\"([^\"]+)\"")
                                .find(msg)?.groupValues?.getOrNull(1) ?: "탈퇴 실패 (${resp.code()})"
                        )
                        .setPositiveButton("확인", null)
                        .show()
                }
            } catch (e: Exception) {
                AlertDialog.Builder(this@SettingsActivity)
                    .setMessage("네트워크 오류: ${e.message}")
                    .setPositiveButton("확인", null)
                    .show()
            }
        }
    }

    override fun onOptionsItemSelected(item: MenuItem): Boolean {
        return when (item.itemId) {
            android.R.id.home -> { finish(); true }
            else -> super.onOptionsItemSelected(item)
        }
    }
}


