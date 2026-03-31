package com.example.qrcode.data.db

import androidx.room.TypeConverter
import org.json.JSONArray

class ImageUriConverters {
    @TypeConverter
    fun fromList(list: List<String>?): String? =
        list?.let { JSONArray(it).toString() }

    @TypeConverter
    fun toList(json: String?): List<String> =
        if (json.isNullOrBlank()) emptyList()
        else (0 until JSONArray(json).length()).map {
            JSONArray(json).getString(it)
        }
}