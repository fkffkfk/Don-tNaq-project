package com.example.qrcode.data.db

import androidx.room.*

@Dao
interface BoardDao {
    @Query("SELECT * FROM board_table ORDER BY id DESC")
    suspend fun getAll(): List<BoardEntity>
    @Query("SELECT * FROM board_table WHERE id = :id LIMIT 1")
    suspend fun getById(id: Int): BoardEntity?
    @Query("SELECT * FROM board_table WHERE isFavorite = 1 ORDER BY id DESC")
    suspend fun getFavorites(): List<BoardEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(board: BoardEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insertAll(items: List<BoardEntity>)
    @Query("UPDATE board_table SET isFavorite = :isFav WHERE id = :id") // ← 추가
    suspend fun setFavorite(id: Int, isFav: Boolean)

    @Update
    suspend fun update(board: BoardEntity)

    @Delete
    suspend fun delete(board: BoardEntity)

}