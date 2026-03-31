package com.example.qrcode.network

import com.example.qrcode.network.networkData.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface ApiService {

    @POST("/users/login")
    suspend fun login(@Body request: LoginRequest): Response<LoginResponse>
    @POST("/users")
    suspend fun signup(@Body body: SignupRequest): Response<SignupResponse>
    //회원가입 이메일인증부분
    @POST("/users/pre-verify")
    suspend fun sendVerificationEmail(
        @Body body: SendVerificationRequest
    ): Response<SignupResponse>
    @GET("/users/verify-status")
    suspend fun checkVerifyStatus(
        @Query("email") email: String
    ): Response<VerifyStatusResponse>
    //탈퇴
    @POST("/withdraw")
    suspend fun withdraw(@Body req: WithdrawRequest): Response<WithdrawResponse>



    // 2. 사용자 전체 스캔 이력
    @GET("/me/scans")
    suspend fun getUserScans(@Query("user_id") userId: Int): Response<List<ScanResult>>

    // 3. 스캔 기록 생성 및 조회
    @POST("/scans")
    suspend fun postScan(@Body body: ScanRequest): Response<ScanResponse>
    @GET("/scans")
    suspend fun getUserScanHistory(@Query("user_id") userId: Int): Response<List<ScanHistoryItem>>
    @GET("/scans")
    suspend fun getRecentScans(@Query("user_id") userId: Int): Response<List<ScanResult>>

    // 4. 모델 예측 수행 및 결과 조회
    @POST("/model-results")
    suspend fun predictMalicious(@Body req: ModelRequest): Response<ModelResponse>
    @GET("/model-results")
    suspend fun getModelResult(@Query("scan_id") scanId: Map<String, Int>): Response<ModelResponse>

    // 5. 통계 조회
    //@GET("/stats")
    //suspend fun getScanStats(): Response<List<StatResult>>
    @GET("/stats")
    suspend fun getWeeklyStats(
        @Query("weeks_back") weeksBack: Int = 0,
        @Query("include_hidden") includeHidden: Int = 0,
        @Query("scope") scope: String = "global",   // 문자열
        @Query("user_id") userId: Int? = null       // nullable
    ): Response<WeeklyStatsResponse>

    @GET("/stats/weeks")
    suspend fun getWeeks(
        @Query("count") count: Int = 8,
        @Query("include_hidden") include_hidden: Int = 0,
        @Query("scope") scope: String,
        @Query("user_id") user_id: Int? = null
    ): Response<WeeksResponse>


    // 6. 보안 QR 생성 및 조회
    // qr스캔api
    @POST("/qr_secure-scan")
    suspend fun secureScan(@Body body: SecureScanRequest): Response<SecureScanResult>

    // 무결성qr저장용
    @POST("/secure-qr")
    suspend fun saveSecureQr(@Body body: SecureQrRequest): Response<Void>
    @GET("/secure-qr")
    suspend fun listSecureQrLogs(@Query("user_id") userId: Int): Response<List<SecureQrLog>>

    // 7. 게시판 기능
    @GET("/posts")
    suspend fun listPosts(
        @Query("limit") limit: Int = 7,
        @Query("offset") offset: Int = 0
    ): Response<List<PostListItem>>

    @GET("/posts/{id}")
    suspend fun getPost(
        @Path("id") id: Long
    ): Response<PostDetail>

    // 관리자만: X-User-Id 헤더가 20이어야 통과 (서버 데코레이터 기준)
    @POST("/posts")
    suspend fun createPost(
        @Header("X-User-Id") adminUserId: Int,
        @Body body: CreatePostRequest
    ): Response<IdResponse>

    @PUT("/posts/{id}")
    suspend fun updatePost(
        @Header("X-User-Id") adminUserId: Int,
        @Path("id") id: Long,
        @Body body: UpdatePostRequest
    ): Response<Unit>

    @DELETE("/posts/{id}")
    suspend fun deletePost(
        @Header("X-User-Id") adminUserId: Int,
        @Path("id") id: Long
    ): Response<Unit>

    // (선택) 서버에 파일 업로드 라우트가 생기면 사용
    @Multipart
    @POST("/upload")
    suspend fun uploadImage(@Part file: MultipartBody.Part): Response<UploadResult>


}

