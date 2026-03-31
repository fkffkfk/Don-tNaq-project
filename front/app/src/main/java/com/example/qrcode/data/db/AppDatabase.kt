package com.example.qrcode.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import androidx.room.migration.Migration
import androidx.sqlite.db.SupportSQLiteDatabase

@Database(
    entities = [User::class, ScannedUrl::class, BoardEntity::class],
    version = 8,
    exportSchema = false
)
@TypeConverters(ImageUriConverters::class)
abstract class AppDatabase : RoomDatabase() {

    abstract fun userDao(): UserDao
    abstract fun scannedUrlDao(): ScannedUrlDao
    abstract fun boardDao(): BoardDao

    companion object {
        @Volatile private var INSTANCE: AppDatabase? = null
        private const val DB_NAME = "my-database.db"

        // (참고) 과거 버전용 마이그레이션들 — 운영 전환 시 사용
        private val MIGRATION_3_4 = object : Migration(3, 4) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
            }
        }
        private val MIGRATION_4_5 = object : Migration(4, 5) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE board_table ADD COLUMN imageUri TEXT")
            }
        }
        private val MIGRATION_5_6 = object : Migration(5, 6) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE board_table ADD COLUMN imageUris TEXT")
            }
        }
        // 필요 시 여기에 6→7 마이그레이션을 정확한 스키마로 추가

        fun getInstance(context: Context): AppDatabase =
            INSTANCE ?: synchronized(this) {
                Room.databaseBuilder(context.applicationContext, AppDatabase::class.java, DB_NAME)
                    // 개발용: 설치돼 있던 DB가 현재 스키마와 다르면 과감히 초기화
                    .fallbackToDestructiveMigrationFrom(1,2,3,4,5,6)
                    // 운영 전환 시에는 위 줄을 지우고 .addMigrations(...) 로 교체
                    .build()
                    .also { INSTANCE = it }
            }
    }
}
