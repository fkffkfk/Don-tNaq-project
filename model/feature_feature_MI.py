from sklearn.feature_selection import mutual_info_classif
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

# 👇 학습에 사용할 피쳐 열 목록
feature_columns = [
    'check_https', 'check_keyword', 'urllength',
    'countspecialchar', 'countnum', 'countletter',
    'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
    'daytime'
]
###########  ▷ 1. 데이터 로드
train_df= pd.read_csv(r'C:\grdu_project\0525_processed_train_dataset.csv')

# MI Matrix 초기화
mi_matrix = pd.DataFrame(index=feature_columns, columns=feature_columns, dtype=float)


features = train_df[feature_columns]
# 각 feature 간 mutual information 계산
for i in feature_columns:
    for j in feature_columns:
        if i == j:
            mi_matrix.loc[i, j] = 1.0  # 자기 자신은 1
        else:
            mi_matrix.loc[i, j] = mutual_info_classif(features[[i]], features[j], discrete_features=True)[0]

# 시각화
plt.figure(figsize=(10, 8))
sns.heatmap(mi_matrix.astype(float), annot=True, cmap="YlGnBu")
plt.title("🔁 Mutual Information Between Features")
plt.tight_layout()
plt.show()
input("Press Enter to exit...")