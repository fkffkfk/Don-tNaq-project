package com.example.qrcode.network.fake


import com.example.qrcode.network.ApiService
import com.example.qrcode.network.networkData.*
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body

class FakeApiService(
    private val USE_FAKE_SERVER: Boolean = true,
    private val logTag: String = "FakeApiService"
) : ApiService {

    // ------------------------
    // 1. 사용자 관련
    // ------------------------
    override suspend fun login(request: LoginRequest): Response<LoginResponse> {
        return Response.success(LoginResponse(message = "로그인 성공(모의)", userId = 1, isAdmin = false))
    }

    override suspend fun signup(body: SignupRequest): Response<SignupResponse> {
        return Response.success(SignupResponse(message = "회원가입 성공(모의)", user_id = 2))
    }

    override suspend fun sendVerificationEmail(body: SendVerificationRequest): Response<SignupResponse> {
        return Response.success(SignupResponse(message = "인증 메일 발송(모의)", resend_available = true))
    }

    override suspend fun checkVerifyStatus(email: String): Response<VerifyStatusResponse> {
        return Response.success(VerifyStatusResponse(verified = true, message = "인증됨(모의)"))
    }

    override suspend fun withdraw(req: WithdrawRequest): Response<WithdrawResponse> {
        return Response.success(WithdrawResponse(message = "회원 탈퇴 완료(모의)"))
    }

    // ------------------------
    // 2~3. 스캔 관련
    // ------------------------
    override suspend fun getUserScans(userId: Int): Response<List<ScanResult>> {
        val dummy = listOf(
            ScanResult(
                1, "https://example.com", "2025-09-27T12:00:00Z", "benign",
                reason = TODO()
            ),
            ScanResult(
                2, "http://malicious.com", "2025-09-26T12:00:00Z", "malicious",
                reason = TODO()
            )
        )
        return Response.success(dummy)
    }

    override suspend fun postScan(body: ScanRequest): Response<ScanResponse> {
        return Response.success(ScanResponse(scan_id = 101))
    }

    override suspend fun getUserScanHistory(userId: Int): Response<List<ScanHistoryItem>> {
        val dummy = listOf(
            ScanHistoryItem(1, "https://example.com", "done", "2025-09-27T10:00:00Z", "benign", 0.05f, "2025-09-27T10:01:00Z"),
            ScanHistoryItem(2, "http://malicious.com", "done", "2025-09-26T10:00:00Z", "malicious", 0.9f, "2025-09-26T10:01:00Z")
        )
        return Response.success(dummy)
    }

    override suspend fun getRecentScans(userId: Int): Response<List<ScanResult>> {
        return getUserScans(userId)
    }

    // ------------------------
    // 4. 모델 예측
    // ------------------------
    override suspend fun predictMalicious(req: ModelRequest): Response<ModelResponse> {
        return Response.success(ModelResponse(
            scan_id = req.scan_id, prediction = "benign", probability = 0.05f,
            message = TODO(),
            reason = TODO()
        ))
    }

    override suspend fun getModelResult(scanId: Map<String, Int>): Response<ModelResponse> {
        TODO("Not yet implemented")
    }



    // ------------------------
    // 5. 통계
    // ------------------------
    override suspend fun getWeeklyStats(
        weeksBack: Int,
        includeHidden: Int,
        scope: String,
        userId: Int?
    ): Response<WeeklyStatsResponse> {
        val summary = WeeklyStatsSummary(total_malicious = 3, unique_users_in_range = 2)
        val days = listOf(
            WeeklyDayStat(0, "Mon", "2025-09-22", 1, 1),
            WeeklyDayStat(1, "Tue", "2025-09-23", 2, 1)
        )
        return Response.success(
            WeeklyStatsResponse(
                week_start = "2025-09-22",
                week_end = "2025-09-28",
                weeks_back = weeksBack,
                include_hidden = includeHidden == 1,
                summary = summary,
                days = days
            )
        )
    }

    override suspend fun getWeeks(
        count: Int,
        include_hidden: Int,
        scope: String,
        user_id: Int?
    ): Response<WeeksResponse> {
        val dummy = listOf(
            WeekItem(weekNo = 39, start = "2025-09-22", end = "2025-09-28", label = "39주차 (09.22~09.28)", scans = Scans(10, 8, 2), uniqueUsers = 3),
            WeekItem(weekNo = 38, start = "2025-09-15", end = "2025-09-21", label = "38주차 (09.15~09.21)", scans = Scans(12, 10, 2), uniqueUsers = 4)
        )
        return Response.success(WeeksResponse(dummy))
    }

    // ------------------------
    // 6. 보안 QR
    // ------------------------
    override suspend fun secureScan(body: SecureScanRequest): Response<SecureScanResult> {
        val benign = body.url.contains("safe") || body.url.contains("example")
        val prediction = if (benign) 0 else 1
        val prob = if (benign) 0.05 else 0.9
        val msg = if (benign) "정상 URL(모의)" else "의심 URL(모의)"
        return Response.success(SecureScanResult(
            msg, prediction, prob, body.scan_id ?: 1000, "fake_user"
        ))
    }

    override suspend fun saveSecureQr(body: SecureQrRequest): Response<Void> {
        return Response.success(null)
    }

    override suspend fun listSecureQrLogs(userId: Int): Response<List<SecureQrLog>> {
        val dummy = listOf(
            SecureQrLog(1, "https://example.com/safe", "fake-sign", "/img1.png", "2025-09-27"),
            SecureQrLog(2, "http://malicious.com", "fake-sign", "/img2.png", "2025-09-26")
        )
        return Response.success(dummy)
    }

    // ------------------------
    // 7. 게시판
    // ------------------------
    override suspend fun listPosts(limit: Int, offset: Int): Response<List<PostListItem>> {
        val dummy = (1..limit).map {
            PostListItem(
                id = (offset + it).toLong(),
                user_id = 1,
                title = "더미 글 $it",
                preview = "이것은 미리보기 $it",
                thumb_url = null,
                image_count = 0,
                created_at = "2025-09-27T12:00:00Z"
            )
        }
        return Response.success(dummy)
    }

    override suspend fun getPost(id: Long): Response<PostDetail> {
        return Response.success(
            PostDetail(
                id = id,
                user_id = 1,
                title = "더미 글 제목 $id",
                content = "더미 본문입니다",
                image_urls = listOf("https://example.com/image1.png"),
                created_at = "2025-09-27T12:00:00Z",
                updated_at = "2025-09-27T12:30:00Z"
            )
        )
    }

    override suspend fun createPost(adminUserId: Int, body: CreatePostRequest): Response<IdResponse> {
        return Response.success(IdResponse(id = 100))
    }

    override suspend fun updatePost(adminUserId: Int, id: Long, body: UpdatePostRequest): Response<Unit> {
        return Response.success(Unit)
    }

    override suspend fun deletePost(adminUserId: Int, id: Long): Response<Unit> {
        return Response.success(Unit)
    }

    // ------------------------
    // 8. 업로드
    // ------------------------
    override suspend fun uploadImage(file: MultipartBody.Part): Response<UploadResult> {
        return Response.success(UploadResult(url = "https://example.com/fake.png"))
    }
}
