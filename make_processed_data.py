import pandas as pd
import random
from feature_module import ExistenceBased,LengthBased,CountBased,DaysBased,DNS,SSL
from feature_extractor import FeatureExtractor
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier
import joblib

from sklearn.feature_selection import mutual_info_classif
import matplotlib.pyplot as plt

from sklearn.ensemble import VotingClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

import seaborn as sns
import joblib


from sklearn.model_selection import cross_validate, StratifiedKFold
import numpy as np





# 👇 학습에 사용할 피쳐 열 목록
feature_columns = [
    'check_https', 'check_keyword', 'countletter',
    'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
    'daytime',
    'is_untrusted_ca','is_weak_protocol','is_weak_key_algo',
    'is_short_lived_cert','is_expired','domain_cn_mismatch',
    'is_self_signed','san_count_high'
]

###########  ▷ 1. 데이터 로드 (기존 학습 데이터셋에 WHOIS CSV파일 합친 데이터셋)
train_df= pd.read_csv(r'C:\grdu_project\model_training\train_whois_dataset.csv')
whois_df = pd.read_csv(r'C:\grdu_project\model_training\traindf_domain.csv')




########### ▷ 2. 특징 추출 
# 1. 문자열
keywords = ["login", "secure", "update", "verify", "urgent", "invoice", "account",
			"banking", "free", "gift", "cash", "paypal", "facebook", "apple","amazon", "password", "admin",
            'yahwagsc.pro','xin','thetollroad','webflow.io','vip','top',
            'ezdrivema','world','t.ly','han.gl','secure','txtag.org',
            'buly.kr','weebly','ezdrive','getipass']

# 5. 문자 개수 기준값
letter_series = train_df['URL'].apply(CountBased.extract_letter)
letter_avg = letter_series.mean()
letter_std = letter_series.std()


# 6. WHOIS 기준값 계산
'''
domain_series = train_df['URL'].apply(DaysBased.extract_domain)
whois_df = domain_series.apply(lambda x: DaysBased.extract_domain_dates(x)).apply(pd.Series)
'''
thresholds = DaysBased.compute_thresholds(whois_df)



# ✅ 여기에서 extractor 생성, FeatureExtractor 객체 생성
extractor = FeatureExtractor(
    
    letter_avg, letter_std, 
    thresholds, keywords
    
)

# 전처리된 feature만 추출
preprocessed= extractor.transform(train_df).reset_index(drop=True)

#기존 데이터셋
original_cols = train_df.reset_index(drop=True)

# 합치기
full_dataset = pd.concat([original_cols, preprocessed], axis=1)


print("🧪 열 확인:", full_dataset .columns.tolist())
full_dataset .to_csv("0602_processed_train_dataset.csv", index=False)
print("✅ 전처리된 학습 데이터셋 저장 완료: processed_train_dataset.csv")

########### ▷ 3. 학습용 X_train, y_train 정의, 검증용 X_val, y_val (8:2)

X = full_dataset[feature_columns]
y = full_dataset['is_malicious'] # 타겟 컬럼

X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

# 학습용 데이터 저장
train_split_df = pd.DataFrame(X_train, columns=feature_columns)
train_split_df['is_malicious'] = y_train.values
train_split_df.to_csv('X_train.csv', index=False)

# 검증용 데이터 저장
val_split_df = pd.DataFrame(X_val, columns=feature_columns)
val_split_df['is_malicious'] = y_val.values
val_split_df.to_csv('X_val.csv', index=False)

print("✅ 학습/검증 데이터셋 CSV로 저장 완료")



#임계값 저장
feature_params = {
    
    'letter_avg': letter_avg,
    'letter_std': letter_std,
    'thresholds': thresholds,
    'keywords': keywords
}
