package com.example.qrcode.util

import android.content.Context
import android.net.Uri
import java.io.File

fun Context.persistToAppFile(srcUri: Uri): File {
    val dir = File(filesDir, "board_images").apply { mkdirs() }
    val name = "${System.currentTimeMillis()}_${srcUri.lastPathSegment?.hashCode()}.jpg"
    val out = File(dir, name)
    contentResolver.openInputStream(srcUri).use { input ->
        out.outputStream().use { output -> requireNotNull(input) { "InputStream null" }.copyTo(output) }
    }
    return out
}