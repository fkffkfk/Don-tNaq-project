import pandas as pd
import joblib
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report



# 🔹 FeatureExtractor 클래스 먼저 정의하거나 불러와야 함
from feature_extractor import FeatureExtractor


#데이터 로드
test_df = pd.read_csv(r'C:\grdu_project\model_training\test_dataset.csv')

# ✅ 2. 기준값 불러오기 (학습 시 저장한 것)
params = joblib.load('0526_feature_params.pkl')

# ✅ 3. FeatureExtractor 인스턴스 생성
extractor = FeatureExtractor(**params)

# ✅ 4. 특징 추출 (전처리)
x_test = extractor.transform(test_df)
y_test = test_df['is_malicious']

# ✅ 5. 모델 불러오기
rf_model = joblib.load('0526rf_model.pkl')
xgb_model = joblib.load('0526xgb_model.pkl')
ensemble_model = joblib.load('0526ensemble_model.pkl')



print("RF 모델 정확도:", rf_model.score(x_test, y_test))
print("XGB 모델 정확도:", xgb_model.score(x_test, y_test))
print("Ensemble 모델 정확도:", ensemble_model.score(x_test, y_test))

for name, model in zip(['RF', 'XGB','ensemble'], [rf_model, xgb_model,ensemble_model]):
    y_pred = model.predict(x_test)
    print(f"\n📊 {name} 모델 평가")
    print("정확도:", accuracy_score(y_test, y_pred))
    print("정밀도:", precision_score(y_test, y_pred))
    print("재현율:", recall_score(y_test, y_pred))
    print("F1 점수:", f1_score(y_test, y_pred))