package com.example.qrcode.network.fake

import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import okhttp3.Request
import okio.Timeout

class FakeCall<T>(private val response: T) : Call<T> {
    override fun enqueue(callback: Callback<T>) {
        callback.onResponse(this, Response.success(response))
    }

    override fun isExecuted() = false
    override fun clone(): Call<T> = this
    override fun isCanceled() = false
    override fun cancel() {}
    override fun execute(): Response<T> = Response.success(response)
    override fun request(): Request = Request.Builder().url("http://localhost").build()

    override fun timeout(): Timeout { return Timeout.NONE }
}
