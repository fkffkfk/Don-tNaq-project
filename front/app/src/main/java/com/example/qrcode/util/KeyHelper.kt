package com.example.qrcode.util

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import android.util.Log
import java.security.KeyPairGenerator
import java.security.KeyStore

object KeyHelper {
    private fun aliasFromEmail(email: String): String {
        val safe = email.trim().lowercase().replace(Regex("[^a-z0-9._-]"), "_")
        return "key_$safe"
    }
    fun generateKeyPairIfNotExists(email: String) {
        val alias = aliasFromEmail(email)
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply {
            load(null)
        }
        if (keyStore.containsAlias(alias)) {
            Log.d("KeyHelper", "키 이미 존재함: $alias")
            return
        }
        val keyPairGenerator = KeyPairGenerator.getInstance(
            KeyProperties.KEY_ALGORITHM_EC,
            "AndroidKeyStore"
        )
        val parameterSpec = KeyGenParameterSpec.Builder(
            alias,
            KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY
        )
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setUserAuthenticationRequired(false)
            .build()
        keyPairGenerator.initialize(parameterSpec)
        keyPairGenerator.generateKeyPair()
        Log.d("KeyHelper", "키 생성 완료: $alias")
    }

    // 공개키 추출
    fun getEncodedPublicKey(email: String): String? {
        val alias = aliasFromEmail(email)
        val keyStore = KeyStore.getInstance("AndroidKeyStore").apply {
            load(null)
        }
        val certificate = keyStore.getCertificate(alias) ?: return null
        val publicKeyBytes = certificate.publicKey.encoded
        return Base64.encodeToString(publicKeyBytes, Base64.NO_WRAP)
    }
}
