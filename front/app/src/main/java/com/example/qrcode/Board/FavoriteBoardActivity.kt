package com.example.qrcode.Board

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import androidx.recyclerview.widget.LinearLayoutManager
import com.example.qrcode.data.db.AppDatabase
import com.example.qrcode.data.db.BoardEntity
import com.example.qrcode.databinding.ActivityFavoriteBoardBinding
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class FavoriteBoardActivity : AppCompatActivity() {
    private lateinit var binding: ActivityFavoriteBoardBinding
    private lateinit var adapter: BoardAdapter
    private val favoriteList = mutableListOf<BoardEntity>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityFavoriteBoardBinding.inflate(layoutInflater)
        setContentView(binding.root)

        adapter = BoardAdapter(favoriteList,
            onItemClick = { item ->
                val intent = Intent(this, BoardDetailActivity::class.java).apply {
                    putExtra("id", item.id)
                }
                startActivity(intent)
            },
            onFavoriteClick = { item ->
                item.isFavorite = !item.isFavorite
                lifecycleScope.launch {
                    AppDatabase.getInstance(this@FavoriteBoardActivity).boardDao().update(item)
                    loadFavorites() // 갱신
                }
            }
        )

        binding.recyclerFavorites.layoutManager = LinearLayoutManager(this)
        binding.recyclerFavorites.adapter = adapter

        loadFavorites()
    }

    private fun loadFavorites() {
        lifecycleScope.launch {
            val dao = AppDatabase.getInstance(this@FavoriteBoardActivity).boardDao()
            val items = withContext(Dispatchers.IO) { dao.getFavorites() }
            favoriteList.clear()
            favoriteList.addAll(items)
            adapter.notifyDataSetChanged()
        }
    }
}
