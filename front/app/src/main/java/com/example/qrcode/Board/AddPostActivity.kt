package com.example.qrcode.Board

import android.net.Uri
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.bumptech.glide.Glide
import com.example.qrcode.databinding.ActivityAddPostBinding
import com.example.qrcode.network.RetrofitClient
import kotlinx.coroutines.launch
import okhttp3.MultipartBody
import java.io.File
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.asRequestBody


class AddPostActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAddPostBinding
    private val selectedUris = mutableListOf<Uri>()

    // 여러 장 선택 (최대 10장 예시)
    private val pickMultiple = registerForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(10)
    ) { uris ->
        selectedUris.clear()
        selectedUris.addAll(uris ?: emptyList())
        // 미리보기는 첫 장만 (간단 버전)
        if (selectedUris.isNotEmpty()) {
            val file = persistToAppFile(selectedUris.first())
            binding.imagePreview.visibility = View.VISIBLE
            Glide.with(this@AddPostActivity)
                .load(file)              // content:// ❌ → File ⭕
                .into(binding.imagePreview)
        } else {
            binding.imagePreview.visibility = View.GONE
        }

    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAddPostBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.btnSelectImage.setOnClickListener {
            pickMultiple.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
        }

        // 서버 연관 부분
        binding.btnSave.setOnClickListener {
            val title = binding.editTitle.text.toString().trim()
            val content = binding.editContent.text.toString().trim()

            // 관리자 체크 (user_id == 6)
            val me = getSharedPreferences("user", MODE_PRIVATE).getInt("user_id", -1)
            if (me != 6) {
                Toast.makeText(this, "관리자만 작성할 수 있습니다.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            if (title.isNotEmpty() && content.isNotEmpty()) {
                lifecycleScope.launch {
                    try {
                        // 1) 선택된 이미지를 서버에 업로드해서 URL 목록 만들기
                        val urls = mutableListOf<String>()
                        for (u in selectedUris) {
                            // content:// → 앱 내부 임시 File 로 복사
                            val file = persistToAppFile(u) // ← 이제 클래스 레벨 메서드라 인식됨
                            val reqFile = file.asRequestBody("image/*".toMediaType())
                            val part = MultipartBody.Part.createFormData("file", file.name, reqFile)


                            val uploadResp = RetrofitClient.api.uploadImage(part)
                            if (uploadResp.isSuccessful) {
                                uploadResp.body()?.url?.let { urls += it }
                            }
                        }

                        // 2) 글 생성 요청 전송
                        val body = com.example.qrcode.network.networkData.CreatePostRequest(
                            title = title,
                            content = content,
                            image_urls = urls
                        )
                        val resp = RetrofitClient.api.createPost(6, body)
                        if (resp.isSuccessful) {
                            Toast.makeText(this@AddPostActivity, "작성 완료", Toast.LENGTH_SHORT).show()
                            finish()
                        } else {
                            Toast.makeText(
                                this@AddPostActivity,
                                "작성 실패: ${resp.code()}",
                                Toast.LENGTH_SHORT
                            ).show()
                        }
                    } catch (e: Exception) {
                        Toast.makeText(
                            this@AddPostActivity,
                            "네트워크 오류: ${e.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            } else {
                Toast.makeText(this, "제목과 내용을 입력해주세요.", Toast.LENGTH_SHORT).show()
            }
        }
    }

    // ✅ onCreate 바깥(클래스 레벨)으로 이동 + private 허용
    private fun persistToAppFile(uri: Uri): File {
        val dir = File(filesDir, "board_images").apply { mkdirs() }
        val name = "${System.currentTimeMillis()}_${uri.lastPathSegment?.hashCode()}.jpg"
        val outFile = File(dir, name)

        contentResolver.openInputStream(uri).use { input ->
            outFile.outputStream().use { output ->
                requireNotNull(input) { "InputStream is null for $uri" }.copyTo(output)
            }
        }
        return outFile
    }
}