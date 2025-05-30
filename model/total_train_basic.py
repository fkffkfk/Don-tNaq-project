import pandas as pd
import random
from feature_module import ExistenceBased,LengthBased,CountBased,DaysBased,DNS
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




# 👇 학습에 사용할 피쳐 열 목록
feature_columns = [
    'check_https', 'check_keyword', 'urllength',
    'countspecialchar', 'countnum', 'countletter',
    'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
    'daytime'
]
###########  ▷ 1. 데이터 로드
train_df= pd.read_csv(r'C:\grdu_project\model_training\train_dataset.csv')


########### ▷ 2. 특징 추출 
# 1. 문자열
keywords = ["login", "secure", "update", "verify", "urgent", "invoice", "account",
			"banking", "free", "gift", "cash", "paypal", "facebook", "apple","amazon", "password", "admin",
            'yahwagsc.pro','xin','thetollroad','webflow.io','vip','top',
            'ezdrivema','world','t.ly','han.gl','secure','txtag.org',
            'buly.kr','weebly','ezdrive','getipass']

# 2. URL 길이 기준값
length_series = train_df['URL'].dropna().apply(lambda x: len(str(x)))
url_avg = length_series.mean()
url_std = length_series.std()


# 3. 특수문자 개수 기준값
schar_series = train_df['URL'].apply(CountBased.counting_specialchar)
schar_avg = schar_series.mean()
schar_std = schar_series.std()

# 4. 숫자 개수 기준값
num_series = train_df['URL'].apply(CountBased.extract_num)
num_avg = num_series.mean()
num_std = num_series.std()

# 5. 문자 개수 기준값
letter_series = train_df['URL'].apply(CountBased.extract_letter)
letter_avg = letter_series.mean()
letter_std = letter_series.std()

# 6. WHOIS 기준값 계산
domain_series = train_df['URL'].apply(DaysBased.extract_domain)
whois_df = domain_series.apply(lambda x: DaysBased.extract_domain_dates(x)).apply(pd.Series)
thresholds = DaysBased.compute_thresholds(whois_df)



train_df.to_csv("0527_processed_train_dataset.csv", index=False)
print("✅ 전처리된 학습 데이터셋 저장 완료: processed_train_dataset.csv")



# ✅ 여기에서 extractor 생성, FeatureExtractor 객체 생성성
extractor = FeatureExtractor(
    url_avg, url_std,
    schar_avg, schar_std,
    num_avg, num_std,
    letter_avg, letter_std,
    thresholds, keywords
)

########### ▷ 3. 학습용 X, y 정의

X_train = extractor.transform(train_df)
y_train = train_df['is_malicious']  # 타겟 컬럼


########### ▷ 4.Mutual Information 계산 =x와 y간 정보 이득량(통계적의존성) 분석 _ 수학적 통계 분석일뿐
mi_scores = mutual_info_classif(X_train, y_train, discrete_features=True)
for f, s in zip(feature_columns, mi_scores):
    print(f"{f:20} → {s:.4f}")


########### ▷ 5.Random Forest 학습 및 Feature Importance 추출
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)
rf_importances = rf_model.feature_importances_  #RF모델이 학습 중 각 feature에 얼마나 많이 의존했는지 정량적으로 계산한 값



########### ▷ 6. XGBoost 학습 & 중요도
xgb_model = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, 
                          use_label_encoder=False, eval_metric='logloss', random_state=42) 
xgb_model.fit(X_train, y_train)
xgb_importances =xgb_model.feature_importances_

###### 앙상블 학습
ensemble_model = VotingClassifier(
    estimators=[('rf', rf_model),('xgb', xgb_model)
    ],
    voting='soft'
)
ensemble_model.fit(X_train, y_train)
ensemble_importances = (rf_importances + xgb_importances) / 2


########### ▷ 7. 모델 객체 저장, 모델 전처리 값 저장
joblib.dump(rf_model,  '0527rf_model.pkl')
joblib.dump(xgb_model, '0527xgb_model.pkl')
joblib.dump(ensemble_model, '0527ensemble_model.pkl')
print("✅ Models saved to disk.")


feature_params = {
    'url_avg' : url_avg,
    'url_std' : url_std,
    'schar_avg': schar_avg,
    'schar_std': schar_std,
    'num_avg': num_avg,
    'num_std': num_std,
    'letter_avg': letter_avg,
    'letter_std': letter_std,
    'thresholds': thresholds,
    'keywords': keywords
}

joblib.dump(feature_params, '0527_feature_params.pkl')
print("✅ 전처리 기준값 저장 완료: 0527_feature_params.pkl")

########### ▷ 8.두 결과를 하나의 DataFrame으로 정리
results_df = pd.DataFrame({
    'Feature': feature_columns,
    'Mutual_Info': mi_scores,
    'RF_Importance': rf_importances,
    'XGB_Importance':xgb_importances,
    'ensemble_Importance':ensemble_importances
}).sort_values(by='Mutual_Info', ascending=False)

print("🔍 Feature 중요도 분석 결과:")
print(results_df)



############ ▷ 9. 시각화 (Mutual Info, RF, XGB)
'''
plt.figure(figsize=(10, 6))
plt.barh(results_df['Feature'], results_df['Mutual_Info'], color='skyblue', label='Mutual Info')
plt.barh(results_df['Feature'], results_df['RF_Importance'], color='orange', alpha=0.6, label='RF Importance')
plt.barh(results_df['Feature'], results_df['XGB_Importance'], color='green', alpha=0.5, label='XGB Importance')
plt.xlabel("Importance Score")
plt.title("📊 Mutual Information vs Random Forest Importance")
plt.legend()
plt.gca().invert_yaxis()
plt.tight_layout()
plt.show()
'''

## 특징_라벨 MI 시각화
plt.figure(figsize=(8,4))
plt.barh(feature_columns, mi_scores, color='skyblue')
plt.xlabel("Mutual Information with Label")
plt.title("📊 Feature vs Label MI")
plt.tight_layout()
plt.show()

importance_matrix = pd.DataFrame({
    'RF': rf_importances,
    'XGB': xgb_importances,
    'Ensemble': (rf_importances + xgb_importances) / 2
}, index=feature_columns).T  # Transpose: 모델을 행, feature를 열

# 시각화
plt.figure(figsize=(10, 5))
sns.heatmap(importance_matrix, annot=True, cmap="YlGnBu")
plt.title("🔥 Feature Importance by Model")
plt.xlabel("Feature")
plt.ylabel("Model")
plt.tight_layout()
plt.show()
input("Press Enter to exit...")


# 1. Random Forest
y_pred_rf = rf_model.predict(X_train)
print("📌 [Random Forest]")
print("Accuracy :", accuracy_score(y_train, y_pred_rf))
print("Precision:", precision_score(y_train, y_pred_rf))
print("Recall   :", recall_score(y_train, y_pred_rf))
print("F1-score :", f1_score(y_train, y_pred_rf))

# 2. XGBoost
y_pred_xgb = xgb_model.predict(X_train)
print("\n📌 [XGBoost]")
print("Accuracy :", accuracy_score(y_train, y_pred_xgb))
print("Precision:", precision_score(y_train, y_pred_xgb))
print("Recall   :", recall_score(y_train, y_pred_xgb))
print("F1-score :", f1_score(y_train, y_pred_xgb))

# 3. 앙상블
y_pred_ensemble = ensemble_model.predict(X_train)
print("\n📌 [Voting Ensemble]")
print("Accuracy :", accuracy_score(y_train, y_pred_ensemble))
print("Precision:", precision_score(y_train, y_pred_ensemble))
print("Recall   :", recall_score(y_train, y_pred_ensemble))
print("F1-score :", f1_score(y_train, y_pred_ensemble))
