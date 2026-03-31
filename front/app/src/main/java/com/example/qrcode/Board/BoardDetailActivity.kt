package com.example.qrcode.Board

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.viewpager2.widget.ViewPager2
import com.bumptech.glide.Glide
import com.example.qrcode.R
import com.example.qrcode.data.db.AppDatabase
import com.example.qrcode.data.db.BoardDao
import com.example.qrcode.data.db.BoardEntity
import com.example.qrcode.databinding.ActivityBoardDetailBinding
import com.example.qrcode.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class BoardDetailActivity : AppCompatActivity() {
    private lateinit var binding: ActivityBoardDetailBinding
    private lateinit var dao: BoardDao
    private var currentBoard: BoardEntity? = null
    private var pagerCallback: ViewPager2.OnPageChangeCallback? = null


    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBoardDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)

        dao = AppDatabase.getInstance(this).boardDao()

        val id = intent.getIntExtra("id", -1)

        lifecycleScope.launch {
            // 1) 관리자 버튼 노출 기준 (user_id == 6)
            val prefs = getSharedPreferences("user", MODE_PRIVATE)
            val isAdmin = (prefs.getInt("user_id", -1) == 6)
            binding.btnEdit.visibility = if (isAdmin) View.VISIBLE else View.GONE
            binding.btnDelete.visibility = if (isAdmin) View.VISIBLE else View.GONE
            binding.btnEdit.setOnClickListener {
                if (id == -1) return@setOnClickListener
                startActivity(
                    Intent(this@BoardDetailActivity, EditPostActivity::class.java)
                        .putExtra("id", id)
                )
            }
            binding.btnDelete.setOnClickListener {
                if (id == -1) return@setOnClickListener
                val dialog = AlertDialog.Builder(this@BoardDetailActivity)
                    .setTitle("삭제 확인")
                    .setMessage("정말 삭제하시겠습니까?")
                    .setPositiveButton("삭제") { _, _ ->
                        lifecycleScope.launch {
                            try {
                                // 관리자 ID 헤더 포함해서 삭제 요청
                                val prefs = getSharedPreferences("user", MODE_PRIVATE)
                                val userId = prefs.getInt("user_id", -1)
                                val resp = RetrofitClient.api.deletePost(userId, id.toLong())

                                if (resp.isSuccessful) {
                                    Toast.makeText(this@BoardDetailActivity, "삭제되었습니다.", Toast.LENGTH_SHORT).show()
                                    finish() // 현재 화면 닫기 → 목록으로 돌아감
                                } else {
                                    Toast.makeText(this@BoardDetailActivity, "삭제 실패: ${resp.code()}", Toast.LENGTH_SHORT).show()
                                }
                            } catch (e: Exception) {
                                e.printStackTrace()
                                Toast.makeText(this@BoardDetailActivity, "삭제 중 오류 발생", Toast.LENGTH_SHORT).show()
                            }
                        }
                    }
                    .setNegativeButton("취소", null)
                    .show()

            }

            // 2) 서버 상세 먼저 시도
            val server = runCatching { RetrofitClient.api.getPost(id.toLong()).body() }.getOrNull()
            if (server != null) {
                // (즐겨찾기 버튼을 위해) Room에 동일 id가 있는지 확인 → 없으면 임시 엔티티 생성
                val existed = withContext(Dispatchers.IO) { dao.getById(id) }
                currentBoard = existed ?: BoardEntity(
                    id = id,
                    title = server.title,
                    content = server.content,
                    imageUris = null,                 // 서버는 image_urls(List<String>)로 받음
                    imageUri = server.image_urls?.firstOrNull(), // 목록용 대표 이미지
                    isFavorite = existed?.isFavorite ?: false
                )
                // existed가 없으면 DB에 넣어두면 즐겨찾기 토글 시 update가 동작함(선택)
                if (existed == null) withContext(Dispatchers.IO) { dao.insert(currentBoard!!) }

                // 제목/본문
                binding.detailTitle.text = server.title
                binding.detailContent.text = server.content


                // 이미지 뷰페이저
                val list = server.image_urls.orEmpty()
                if (list.isNotEmpty()) {
                    binding.imagePager.visibility = View.VISIBLE
                    binding.imagePager.adapter = ImagePagerAdapter(list)
                    binding.imagePager.offscreenPageLimit = minOf(3, list.size)
                    binding.imagePager.post { binding.imagePager.adapter?.notifyDataSetChanged() }

                    val total = list.size
                    if (total > 1) {
                        binding.pageIndicator.visibility = View.VISIBLE
                        binding.pageIndicator.text = "1/$total"
                        pagerCallback?.let { binding.imagePager.unregisterOnPageChangeCallback(it) }
                        pagerCallback = object : ViewPager2.OnPageChangeCallback() {
                            override fun onPageSelected(position: Int) {
                                binding.pageIndicator.text = "${position + 1}/$total"
                            }
                        }
                        binding.imagePager.registerOnPageChangeCallback(pagerCallback!!)
                    } else {
                        binding.pageIndicator.visibility = View.GONE
                    }
                } else {
                    binding.imagePager.visibility = View.GONE
                    binding.pageIndicator.visibility = View.GONE
                }

                // 즐겨찾기 아이콘/토글 유지
                updateFavoriteIcon(currentBoard!!.isFavorite)
                binding.btnDetailFavorite.setOnClickListener {
                    currentBoard?.let { b ->
                        b.isFavorite = !b.isFavorite
                        updateFavoriteIcon(b.isFavorite)
                        lifecycleScope.launch(Dispatchers.IO) { dao.update(b) }
                    }
                }

                // ✅ 서버 상세 성공했으므로 여기서 종료 (Room 폴백 불필요)
                return@launch
            }

            // 3) 서버 실패 → Room 폴백 (기존 코드 유지)
            currentBoard = withContext(Dispatchers.IO) { dao.getById(id) }
            Log.d("BoardDetail", "조회된 BoardEntity=$currentBoard")

            currentBoard?.let { board ->
                binding.detailTitle.text = board.title
                binding.detailContent.text = board.content
                updateFavoriteIcon(board.isFavorite)

                val list = when {
                    !board.imageUris.isNullOrEmpty() -> board.imageUris!!
                    !board.imageUri.isNullOrBlank()  -> listOf(board.imageUri!!)
                    else -> emptyList()
                }

                if (list.isNotEmpty()) {
                    binding.imagePager.visibility = View.VISIBLE
                    binding.imagePager.adapter = ImagePagerAdapter(list)
                    binding.imagePager.offscreenPageLimit = minOf(3, list.size)
                    binding.imagePager.post { binding.imagePager.adapter?.notifyDataSetChanged() }

                    val total = list.size
                    if (total > 1) {
                        binding.pageIndicator.visibility = View.VISIBLE
                        binding.pageIndicator.text = "1/$total"
                        pagerCallback?.let { binding.imagePager.unregisterOnPageChangeCallback(it) }
                        pagerCallback = object : ViewPager2.OnPageChangeCallback() {
                            override fun onPageSelected(position: Int) {
                                binding.pageIndicator.text = "${position + 1}/$total"
                            }
                        }
                        binding.imagePager.registerOnPageChangeCallback(pagerCallback!!)
                    } else {
                        binding.pageIndicator.visibility = View.GONE
                    }
                } else {
                    binding.imagePager.visibility = View.GONE
                    binding.pageIndicator.visibility = View.GONE
                }

                binding.btnDetailFavorite.setOnClickListener {
                    board.isFavorite = !board.isFavorite
                    updateFavoriteIcon(board.isFavorite)
                    lifecycleScope.launch(Dispatchers.IO) { dao.update(board) }
                }

            }
        }
    }

    private fun updateFavoriteIcon(isFavorite: Boolean) {
        val res = if (isFavorite) R.drawable.ic_star else R.drawable.ic_star_border
        binding.btnDetailFavorite.setImageResource(res)
    }
}