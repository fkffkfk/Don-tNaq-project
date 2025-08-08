import joblib
import pandas as pd

# 모델 로드
model = joblib.load("0624_rfxgbcat_model.pkl")

# 입력 예시
test_input = {
    'check_https': 1,
    'check_keyword': 0,
    'countletter': 40,
    'ttl': 3600,
    'ns_match': 1,
    'dns_query_success': 1,
    'DNS_mal': 0,
    'daytime': 120,
    'is_untrusted_ca': 0,
    'is_weak_protocol': 0,
    'is_weak_key_algo': 0,
    'is_short_lived_cert': 0,
    'is_expired': 0,
    'domain_cn_mismatch': 0,
    'is_self_signed': 0,
    'san_count_high': 0
}

input_df = pd.DataFrame([test_input])

# 예측 실행
result = int(model.predict(input_df)[0])
score = float(model.predict_proba(input_df)[0][1])

print("✅ 예측 결과:")
print(f"Result: {result}")
print(f"Score: {score:.4f}")
