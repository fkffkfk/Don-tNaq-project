package com.example.qrcode.Board


import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.bumptech.glide.Glide
import com.example.qrcode.R
import com.example.qrcode.data.db.BoardEntity
import com.example.qrcode.databinding.ItemBoardBinding

class BoardAdapter(
    private val items: List<BoardEntity>,
    private val onItemClick: (BoardEntity) -> Unit,
    private val onFavoriteClick: (BoardEntity) -> Unit
) : RecyclerView.Adapter<BoardAdapter.BoardViewHolder>() {

    inner class BoardViewHolder(val binding: ItemBoardBinding) :
        RecyclerView.ViewHolder(binding.root) {
        fun bind(item: BoardEntity){
            binding.textTitle.text = item.title
            binding.btnFavorite.setImageResource(
                if (item.isFavorite) R.drawable.ic_star else R.drawable.ic_star_border
            )

            // 이미지 표시 추가
            // 첫 번째 이미지 우선 사용 (여러 장 → 첫 장, 아니면 단일)
            val first = item.imageUris?.firstOrNull() ?: item.imageUri

            Log.d("BoardAdapter", "bind: title=${item.title}, first=$first, imageUris=${item.imageUris}")

            if (!first.isNullOrBlank()) {
                binding.imagePreview.visibility = View.VISIBLE
                Glide.with(binding.root)
                    .load(first)  // String 그대로 넣어도 됨
                    .into(binding.imagePreview)
            } else {
                binding.imagePreview.visibility = View.GONE
            }


            binding.root.setOnClickListener { onItemClick(item) }
            binding.btnFavorite.setOnClickListener {
                onFavoriteClick(item)
                notifyItemChanged(adapterPosition)
            }
        }
    }


    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): BoardViewHolder {
        val binding = ItemBoardBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return BoardViewHolder(binding)
    }

    override fun getItemCount() = items.size

    override fun onBindViewHolder(holder: BoardViewHolder, position: Int) {
        holder.bind(items[position])
    }
}