import pandas as pd
import joblib
from pathlib import Path

# === 입력: 전처리된 CSV 경로 ===
PROC_CSV = r"1015_train.csv"  # 본인 경로로
OUT_PKL  = r"1015_feature_params.pkl"           # 저장 경로

# 학습 때 썼던 키워드 리스트를 그대로 넣으세요
keywords = ["login","secure","update","verify","urgent","invoice","account",
            "banking","free","gift","cash","paypal","facebook","apple","amazon",
            "password","admin",'yahwagsc.pro','xin','thetollroad','webflow.io',
            'vip','top','ezdrivema','world','t.ly','han.gl','secure','txtag.org',
            'buly.kr','weebly','ezdrive','getipass']

df = pd.read_csv(PROC_CSV)

# 전처리 결과에 연속형 피처가 있으면 그대로 평균/표준편차 복원 가능
url_avg  = df["url_length"].mean()
url_std  = df["url_length"].std()
schar_avg = df["specialchar_count"].mean()
schar_std = df["specialchar_count"].std()
letter_avg = df["countletter"].mean()
letter_std = df["countletter"].std()

feature_params = {
    "url_avg": url_avg,
    "url_std": url_std,
    "schar_avg": schar_avg,
    "schar_std": schar_std,
    "letter_avg": letter_avg,
    "letter_std": letter_std,
    "keywords": keywords,

    "feature_columns": [
        "check_https","check_keyword","url_length","specialchar_count","countletter",
        "ttl","ns_match","dns_query_success","DNS_mal",
        "is_untrusted_ca","is_weak_protocol","is_weak_key_algo",
        "is_short_lived_cert","is_expired","domain_cn_mismatch",
        "is_self_signed","san_count_high"
    ],
}

Path(OUT_PKL).parent.mkdir(parents=True, exist_ok=True)
joblib.dump(feature_params, OUT_PKL)
print("복원 완료 ->", OUT_PKL)
