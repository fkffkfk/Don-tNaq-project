package com.example.qrcode.Board

import android.content.Intent
import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.appcompat.app.AppCompatActivity
import androidx.fragment.app.Fragment
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.qrcode.data.db.AppDatabase
import com.example.qrcode.data.db.BoardEntity
import com.example.qrcode.databinding.FragmentBoardBinding
import com.example.qrcode.network.RetrofitClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class BoardFragment : Fragment() {
    private lateinit var binding: FragmentBoardBinding
    private lateinit var adapter: BoardAdapter
    private val boardList = mutableListOf<BoardEntity>()

    override fun onCreateView(
        inflater: LayoutInflater,
        container: ViewGroup?,
        savedInstanceState: Bundle?
    ): View {
        binding = FragmentBoardBinding.inflate(inflater, container, false)
        adapter = BoardAdapter(
            boardList,
            onItemClick = { item -> startActivity(
                Intent(requireContext(), BoardDetailActivity::class.java)
                    .putExtra("id", item.id)
            )},
            onFavoriteClick = { item ->
                val newFav = !item.isFavorite
                val idx = boardList.indexOfFirst { it.id == item.id }
                if (idx >= 0) {
                    // 1) 메모리 즉시 반영
                    boardList[idx] = boardList[idx].copy(isFavorite = newFav)
                    adapter.notifyItemChanged(idx)
                }

                // 2) Room 반영 (레코드가 없을 가능성 대비 upsert or 부분 업데이트)
                lifecycleScope.launch(Dispatchers.IO) {
                    val dao = AppDatabase.getInstance(requireContext()).boardDao()
                    // 레코드 없을 수도 있으니 insert(REPLACE)로 안전하게 넣고
                    dao.insert(item.copy(isFavorite = newFav))
                    // 필요하면 부분 업데이트만 써도 됨: dao.setFavorite(item.id, newFav)
                }
            }
        )

        //서버연결후 관리자 계정호출
        val prefs = binding.root.context.getSharedPreferences("user", AppCompatActivity.MODE_PRIVATE)
        val isAdmin = (prefs.getInt("user_id", -1) == 6)
        binding.btnAddPost.visibility = if (isAdmin) View.VISIBLE else View.GONE

        // 📌 관리자만 버튼 보이도록
        binding.btnAddPost.visibility = if (isAdmin) View.VISIBLE else View.GONE

        // 📌 버튼 클릭 시 글쓰기 화면 이동
        binding.btnAddPost.setOnClickListener {
            startActivity(Intent(requireContext(), AddPostActivity::class.java))
        }

        binding.recyclerBoard.layoutManager = LinearLayoutManager(requireContext())
        binding.recyclerBoard.adapter = adapter

        loadBoardItems()
        return binding.root
    }

    override fun onResume() {
        super.onResume()
        loadBoardItems() // 새 게시글 반영
    }
    private fun loadBoardItems() {
        lifecycleScope.launch {
            runCatching {
                val resp = RetrofitClient.api.listPosts(limit = 20, offset = 0)
                val list = resp.body().orEmpty()

                val dao = AppDatabase.getInstance(requireContext()).boardDao()
                val localFavorites = withContext(Dispatchers.IO) { dao.getFavorites() }
                    .associateBy { it.id }

                // 서버 → 화면 모델
                val mapped = list.map { dto ->
                    BoardEntity(
                        id = dto.id.toInt(),
                        title = dto.title,
                        content = dto.preview ?: "",
                        imageUris = null,
                        imageUri = dto.thumb_url,
                        isFavorite = localFavorites[dto.id.toInt()]?.isFavorite ?: false
                    )
                }

                // 🔴 Room에 동기화 (Upsert)
                withContext(Dispatchers.IO) { dao.insertAll(mapped) }

                // 화면 갱신
                boardList.clear()
                boardList.addAll(mapped)
                adapter.notifyDataSetChanged()
            }.onFailure {
                val dao = AppDatabase.getInstance(requireContext()).boardDao()
                val items = withContext(Dispatchers.IO) { dao.getAll() }
                boardList.clear()
                boardList.addAll(items)
                adapter.notifyDataSetChanged()
            }
        }
    }

}

