package com.example.qrcode.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "board_table")
data class BoardEntity(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val title: String,
    val content: String,
    var imageUri: String? = null,
    var imageUris: List<String>? = null,
    var isFavorite: Boolean = false
)