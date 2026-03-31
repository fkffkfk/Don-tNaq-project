package com.example.qrcode.auth

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.example.qrcode.R
import com.example.qrcode.network.RetrofitClient
import com.example.qrcode.network.networkData.*
import com.example.qrcode.util.KeyHelper
import kotlinx.coroutines.launch

class SignupEmailActivity : AppCompatActivity() {

    private lateinit var emailContainer: View
    private lateinit var passwordContainer: View

    private lateinit var editEmail: EditText
    private lateinit var editPassword1: EditText
    private lateinit var editPassword2: EditText
    private lateinit var btnNext: Button        // 인증 메일 보내기
    private lateinit var btnRecieve: Button     // 인증 완료(상태 확인)
    private lateinit var btnFinish: Button      // 가입 완료

    private var stagedEmail: String? = null     // 메일 발송된 이메일 보관

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_signup_email)

        emailContainer = findViewById(R.id.emailContainer)
        passwordContainer = findViewById(R.id.passwordContainer)
        editEmail = findViewById(R.id.editEmail)
        editPassword1 = findViewById(R.id.editPassword1)
        editPassword2 = findViewById(R.id.editPassword2)
        btnNext = findViewById(R.id.btnNext)
        btnRecieve = findViewById(R.id.btnRecieve)
        btnFinish = findViewById(R.id.btnFinish)

        // 1) 인증 메일 보내기
        btnNext.setOnClickListener {
            val email = editEmail.text.toString().trim().lowercase()
            if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                toast("유효한 이메일을 입력하세요")
                return@setOnClickListener
            }

            // 이메일에 해당하는 키쌍 생성안된경우 예외처리
            try { KeyHelper.generateKeyPairIfNotExists(email) } catch (e: Exception) {
                toast("키스토어 오류: ${e.message}"); return@setOnClickListener
            }
            val derBase64 = KeyHelper.getEncodedPublicKey(email)

            lifecycleScope.launch {
                try {
                    btnNext.isEnabled = false
                    val res = RetrofitClient.api.sendVerificationEmail(
                        SendVerificationRequest(email = email, public_key = derBase64)
                    )
                    btnNext.isEnabled = true

                    if (res.isSuccessful) {
                        stagedEmail = email
                        toast(res.body()?.message ?: "인증 메일을 보냈습니다. 메일함을 확인하세요.")
                        // UI 잠그기 + 버튼 전환
                        editEmail.isEnabled = false
                        btnNext.visibility = View.GONE
                        btnRecieve.visibility = View.VISIBLE
                    } else {
                        toast(res.errorBody()?.string() ?: "인증 메일 발송 실패")
                    }
                } catch (e: Exception) {
                    btnNext.isEnabled = true
                    toast("네트워크 오류: ${e.message}")
                }
            }
        }

        // 2) 인증 완료(상태 확인)
        btnRecieve.setOnClickListener {
            val email = stagedEmail ?: editEmail.text.toString().trim().lowercase()
            if (!android.util.Patterns.EMAIL_ADDRESS.matcher(email).matches()) {
                toast("이메일을 다시 확인하세요"); return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    btnRecieve.isEnabled = false
                    val res = RetrofitClient.api.checkVerifyStatus(email)
                    btnRecieve.isEnabled = true

                    if (res.isSuccessful && res.body()?.verified == true) {
                        toast("이메일 인증이 완료되었습니다. 비밀번호를 설정해 주세요.")
                        emailContainer.visibility = View.GONE
                        passwordContainer.visibility = View.VISIBLE
                    } else {
                        toast(res.body()?.message ?: "아직 인증이 완료되지 않았습니다.")
                    }
                } catch (e: Exception) {
                    btnRecieve.isEnabled = true
                    toast("네트워크 오류: ${e.message}")
                }
            }
        }

        // 3) 비밀번호 설정 → 최종 회원가입
        btnFinish.setOnClickListener {
            val email = stagedEmail ?: run {
                toast("이메일 인증부터 진행해 주세요."); return@setOnClickListener
            }
            val p1 = editPassword1.text?.toString()?.trim().orEmpty()
            val p2 = editPassword2.text?.toString()?.trim().orEmpty()
            if (p1.length < 8) { toast("비밀번호는 8자 이상이어야 합니다."); return@setOnClickListener }
            if (p1 != p2) { toast("비밀번호가 일치하지 않습니다."); return@setOnClickListener }

            lifecycleScope.launch {
                try {
                    btnFinish.isEnabled = false
                    val req = SignupRequest(
                        userName = email,              // 일단 서버에서 required라 email로 둠, optional되면 없애도됨
                        userPassword = p1,
                        public_key = KeyHelper.getEncodedPublicKey(email) ?: "",
                        email = email
                    )
                    // 서버는 verified=true인 이메일만 최종 가입 허용
                    val res = RetrofitClient.api.signup(req)
                    btnFinish.isEnabled = true

                    if (res.isSuccessful) {
                        toast(res.body()?.message ?: "회원가입이 완료되었습니다.")
                        val intent = Intent(this@SignupEmailActivity, AuthActivity::class.java)
                        intent.putExtra("prefill_email", email)   // 방금 가입한 이메일 전달
                        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK)
                        startActivity(intent)
                        finish()
                    } else {
                        toast(res.errorBody()?.string() ?: "회원가입 실패")
                    }
                } catch (e: Exception) {
                    btnFinish.isEnabled = true
                    toast("네트워크 오류: ${e.message}")
                }
            }
        }
    }

    private fun toast(msg: String) =
        Toast.makeText(this, msg, Toast.LENGTH_LONG).show()
}



