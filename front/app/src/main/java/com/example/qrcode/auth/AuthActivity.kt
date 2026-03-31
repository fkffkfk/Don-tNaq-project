package com.example.qrcode.auth

import android.content.Intent
import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.EditText
import android.widget.Toast

import androidx.appcompat.app.AppCompatActivity
import androidx.appcompat.app.AppCompatDelegate
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.MainActivity
import com.example.qrcode.R
import com.example.qrcode.network.RetrofitClient.api
import com.example.qrcode.network.networkData.LoginRequest
import kotlinx.coroutines.launch



class AuthActivity : AppCompatActivity() {

    private lateinit var emailEditText: EditText
    private lateinit var passwordEditText: EditText
    private lateinit var loginButton: Button
    private lateinit var signupButton: Button

    //이메일 형식 검증
    private fun isValidEmail(email: String): Boolean {
        return android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_auth)

        val prefs = getSharedPreferences("user", MODE_PRIVATE)
        val isDark = prefs.getBoolean("dark_mode", false)
        AppCompatDelegate.setDefaultNightMode(
            if (isDark) AppCompatDelegate.MODE_NIGHT_YES
            else AppCompatDelegate.MODE_NIGHT_NO
        )

        // UI 연결
        emailEditText = findViewById(R.id.editEmail)
        passwordEditText = findViewById(R.id.editPassword)
        loginButton = findViewById(R.id.btnLogin)
        signupButton = findViewById(R.id.btnSignup)

        // 회원가입 완료 후 넘어올 때 이메일 미리 채워넣기
        val prefill = intent.getStringExtra("prefill_email")
        val cameFromSignup = !prefill.isNullOrEmpty()
        if (cameFromSignup) {
            emailEditText.setText(prefill)
            passwordEditText.requestFocus()
        }

        // 자동로그인 조건: auto_login=true 이고 email값이 저장되있을대
        val auto = prefs.getBoolean("auto_login", false)
        val email = prefs.getString("email", null)


        if (!cameFromSignup && auto && (email != null)) {
            val intent = Intent(this, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
            }
            startActivity(intent)
            finish()
            return
        }


        // 로그인 버튼
        // AuthActivity.kt — 로그인 버튼 클릭 리스너 통째로 교체
        loginButton.setOnClickListener {
            val email = emailEditText.text.toString().trim()
            val password = passwordEditText.text.toString().trim()
            if (!isValidEmail(email)) {
                Toast.makeText(this, "유효한 이메일 주소를 입력하세요.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (password.isEmpty()) {
                Toast.makeText(this, "비밀번호를 입력하세요.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    val resp = api.login(LoginRequest(email, password))
                    if (resp.isSuccessful) {
                        val body = resp.body()

                        // userId가 null일경우
                        val uid = body?.userId ?: -1
                        if (uid <= 0) {
                            Toast.makeText(
                                this@AuthActivity,
                                "로그인 응답에 user_id가 없습니다.",
                                Toast.LENGTH_SHORT
                            ).show()
                            Log.e("LOGIN", "missing user_id in response: $body")
                            return@launch
                        }

                        body?.let { it1 ->
                            val sp = getSharedPreferences("user", MODE_PRIVATE)
                            val currentAuto = sp.getBoolean("auto_login", false) // 기존 토글 유지

                            sp.edit()
                                .putString("email", email)
                                .putInt("user_id", uid)
                                .putBoolean("is_admin", it1.isAdmin)
                                .putBoolean("auto_login", currentAuto) // 자동로그인 상태 반영
                                .apply()
                        }

                        Toast.makeText(this@AuthActivity, "로그인 성공", Toast.LENGTH_SHORT).show()
                        startActivity(Intent(this@AuthActivity, MainActivity::class.java))
                        finish()
                    } else if (resp.code() == 401) {
                        Toast.makeText(
                            this@AuthActivity,
                            "이메일 또는 비밀번호가 올바르지 않습니다.",
                            Toast.LENGTH_SHORT
                        ).show()
                    } else if (resp.code() == 403) {
                        Toast.makeText(
                            this@AuthActivity,
                            "이메일 인증 후 로그인할 수 있습니다.",
                            Toast.LENGTH_LONG
                        ).show()
                    } else {
                        Log.e("LOGIN", "code=${resp.code()} msg=${resp.errorBody()?.string()}")
                        Toast.makeText(
                            this@AuthActivity,
                            "로그인 실패: ${resp.code()}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                } catch (e: Exception) {
                    Log.e("LOGIN", "network error", e)
                    Toast.makeText(this@AuthActivity, "네트워크 오류: ${e.message}", Toast.LENGTH_SHORT)
                        .show()
                }
            }

        }
        // 회원가입 버튼
        signupButton.setOnClickListener {
            // ✅ 회원가입: 이메일 입력 전용 화면으로 이동만 수행
            startActivity(Intent(this, SignupEmailActivity::class.java))
        }

        fun goToMain() {
            val intent = Intent(this, MainActivity::class.java)
            startActivity(intent)
            finish()
        }
    }}