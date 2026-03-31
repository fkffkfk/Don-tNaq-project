package com.example.qrcode.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.Query

@Dao
interface ScannedUrlDao {

    @Insert
    suspend fun insertUrl(scannedUrl: ScannedUrl)

    @Query("SELECT * FROM scanned_urls ORDER BY timestamp DESC")
    suspend fun getAllUrls(): List<ScannedUrl>

    @Query("SELECT * FROM scanned_urls WHERE email = :email ORDER BY timestamp DESC")
    suspend fun getUrlsByUser(email: String): List<ScannedUrl>

}
