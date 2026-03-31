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
import com.example.qrcode.databinding.ActivityEditPostBinding
import com.example.qrcode.network.RetrofitClient
import com.example.qrcode.network.networkData.UpdatePostRequest
import kotlinx.coroutines.launch
import okhttp3.MultipartBody
import okhttp3.MediaType.Companion.toMediaType   // OkHttp 4.x
import okhttp3.RequestBody.Companion.asRequestBody
import java.io.File

class EditPostActivity : AppCompatActivity() {
    private lateinit var binding: ActivityEditPostBinding
    private var postId = -1
    private val selectedUris = mutableListOf<Uri>()

    private val pickMultiple = registerForActivityResult(
        ActivityResultContracts.PickMultipleVisualMedia(10)
    ) { uris ->
        selectedUris.clear()
        selectedUris.addAll(uris ?: emptyList())
        val preview = selectedUris.firstOrNull()
        if (preview != null) {
            binding.imagePreview.visibility = View.VISIBLE
            Glide.with(this@EditPostActivity).load(preview).into(binding.imagePreview)
        } else {
            binding.imagePreview.visibility = View.GONE
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityEditPostBinding.inflate(layoutInflater)
        setContentView(binding.root)

        postId = intent.getIntExtra("id", -1)

        // 1) 화면 진입 시 서버에서 현재 글 상세 불러오기
        lifecycleScope.launch {
            try {
                val resp = RetrofitClient.api.getPost(postId.toLong())
                val detail = resp.body()
                if (resp.isSuccessful && detail != null) {
                    binding.editTitle.setText(detail.title)
                    binding.editContent.setText(detail.content)
                    val first = detail.image_urls?.firstOrNull()
                    if (!first.isNullOrBlank()) {
                        binding.imagePreview.visibility = View.VISIBLE
                        Glide.with(this@EditPostActivity).load(first).into(binding.imagePreview)
                    } else {
                        binding.imagePreview.visibility = View.GONE
                    }
                } else {
                    Toast.makeText(this@EditPostActivity, "글 정보를 불러오지 못했습니다.", Toast.LENGTH_SHORT).show()
                    finish()
                }
            } catch (e: Exception) {
                Toast.makeText(this@EditPostActivity, "네트워크 오류: ${e.message}", Toast.LENGTH_SHORT).show()
                finish()
            }
        }

        binding.btnSelectImage.setOnClickListener {
            pickMultiple.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
        }

        // 2) 수정 저장 → 서버 PUT
        binding.btnUpdate.setOnClickListener {
            val me = getSharedPreferences("user", MODE_PRIVATE).getInt("user_id", -1)
            if (me != 6) {
                Toast.makeText(this, "관리자만 수정할 수 있습니다.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val newTitle = binding.editTitle.text.toString().trim()
            val newContent = binding.editContent.text.toString().trim()

            if (newTitle.isBlank() || newContent.isBlank() || postId == -1) {
                Toast.makeText(this, "내용을 모두 입력해주세요.", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                try {
                    // (옵션) 이미지 업로드 라우트가 있을 때만 활성화
                    // 없으면 urls = emptyList() 그대로 둬도 됨
                    val urls = mutableListOf<String>()
                    for (u in selectedUris) {
                        val file = persistToAppFile(u)  // content:// → 내부 파일로 복사
                        val req = file.asRequestBody("image/*".toMediaType())
                        val part = MultipartBody.Part.createFormData("file", file.name, req)

                        val up = RetrofitClient.api.uploadImage(part) // 서버에 /upload가 있을 때만 성공
                        if (up.isSuccessful) up.body()?.url?.let { urls += it }
                    }

                    val body = UpdatePostRequest(
                        title = newTitle,
                        content = newContent,
                        image_urls = urls.takeIf { it.isNotEmpty() } ?: emptyList()
                    )

                    val resp = RetrofitClient.api.updatePost(
                        adminUserId = 6,            // 서버 admin_required와 일치
                        id = postId.toLong(),
                        body = body
                    )
                    if (resp.isSuccessful) {
                        Toast.makeText(this@EditPostActivity, "수정 완료", Toast.LENGTH_SHORT).show()
                        finish()
                    } else {
                        Toast.makeText(this@EditPostActivity, "수정 실패: ${resp.code()}", Toast.LENGTH_SHORT).show()
                    }
                } catch (e: Exception) {
                    Toast.makeText(this@EditPostActivity, "네트워크 오류: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    // 업로드용: content:// → 앱 내부 파일로 복사
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
