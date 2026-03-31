package com.example.qrcode.network


import com.example.qrcode.network.fake.FakeApiService
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object AppConfig {
    //서버없이 연결할때 true로 변경해야됨
    //const val IS_LOCAL_MODE = true
    const val IS_LOCAL_MODE = false
}

object RetrofitClient {
    //private const val BASE_URL = "http://192.168.199.218:5000/"
    private const val BASE_URL = "https://adversarially-proapproval-trace.ngrok-free.dev/"
        //"http://127.0.0.1:5000/"

    // ✅ timeout 설정 추가
    private val okHttpClient = OkHttpClient.Builder()
        .connectTimeout(30, TimeUnit.SECONDS)   // 서버 연결 대기
        .readTimeout(60, TimeUnit.SECONDS)      // 서버 응답 대기 (이게 중요)
        .writeTimeout(60, TimeUnit.SECONDS)     // 요청 전송 대기
        .retryOnConnectionFailure(true)         // 연결 실패 시 재시도
        .build()

    val api: ApiService by lazy {
        if (AppConfig.IS_LOCAL_MODE) {
            FakeApiService()
        } else {
            Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(okHttpClient)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(ApiService::class.java)

        }
    }
}
