plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.kapt)
}

android {
    namespace = "com.example.qrcode"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.example.qrcode"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "1.0"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        viewBinding = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.activity)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.lifecycle.livedata.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)

    implementation ("androidx.constraintlayout:constraintlayout:2.1.4")

    //  Room 필수
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")


    dependencies {
        //scan 기능
        implementation("com.google.mlkit:barcode-scanning:17.2.0")
        implementation("androidx.camera:camera-core:1.3.1")
        implementation("androidx.camera:camera-camera2:1.3.1")
        implementation("androidx.camera:camera-lifecycle:1.3.1")
        implementation("androidx.camera:camera-view:1.3.1")

        // OpenGraph 정보 파싱용
        implementation ("org.jsoup:jsoup:1.16.1")
        implementation ("com.github.bumptech.glide:glide:4.15.1")
        kapt ("com.github.bumptech.glide:compiler:4.15.1")


        //qr생성 기능
        implementation("com.google.zxing:core:3.5.2")

    }

    // Retrofit & Gson
    implementation ("com.squareup.retrofit2:retrofit:2.9.0")
    implementation ("com.squareup.retrofit2:converter-gson:2.9.0")

    //통계 그래프
    implementation("com.github.PhilJay:MPAndroidChart:v3.1.0")
    implementation ("com.google.android.material:material:1.12.0")
    implementation ("androidx.fragment:fragment-ktx:1.8.2" )         // viewModels()
    implementation ("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4") // lifecycleScope
    implementation ("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    //Glide 게시판 이미지넣기
    implementation("androidx.viewpager2:viewpager2:1.0.0")
    implementation("com.github.bumptech.glide:glide:4.16.0") // 이미 있으면 생략
    kapt("com.github.bumptech.glide:compiler:4.16.0")

    //gradle에 OkHttp 4.x를 확실히 추가
    implementation("com.squareup.okhttp3:okhttp:4.11.0")  // 또는 4.12.x
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")

    //color PICKER쓰게되면..
    //implementation ("com.github.QuadFlask:colorpicker:0.0.13")
    //gif 스플래쉬
    implementation ("com.github.bumptech.glide:glide:4.16.0")


}