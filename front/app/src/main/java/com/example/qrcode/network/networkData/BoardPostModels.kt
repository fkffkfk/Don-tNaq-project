package com.example.qrcode.network.networkData

// ── 목록 아이템 (GET /posts)
data class PostListItem(
    val id: Long,
    val user_id: Long,
    val title: String,
    val preview: String?,     // LEFT(content,120)로 내려오는 미리보기
    val thumb_url: String?,   // 서버가 생성한 썸네일(없을 수도)
    val image_count: Int?,    // 이미지 개수(없을 수도)
    val created_at: String
)

// ── 상세 (GET /posts/{id})
data class PostDetail(
    val id: Long,
    val user_id: Long,
    val title: String,
    val content: String,
    val image_urls: List<String>?,  // 서버가 [] 또는 null로 줄 수 있음
    val created_at: String,
    val updated_at: String
)

// ── 생성/수정 요청 바디 (POST /posts, PUT /posts/{id})
data class CreatePostRequest(
    val title: String,
    val content: String,
    val image_urls: List<String> = emptyList()
)
typealias UpdatePostRequest = CreatePostRequest

// ── 생성 응답 {"id": <newId>}
data class IdResponse(val id: Long)

// (선택) 업로드 응답이 있다면 이렇게 사용: { "url": "https://...." }
data class UploadResult(val url: String)
