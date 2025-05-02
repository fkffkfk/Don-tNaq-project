import pandas as pd
import random
from feature_module import ExistenceBased,LengthBased,CountBased,DaysBased,DNS

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from xgboost import XGBClassifier
import joblib


# 👇 학습에 사용할 피쳐 열 목록
feature_columns = [
    'check_https', 'check_keyword', 'urllength',
    'countspecialchar', 'countnum', 'countletter',
    'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
    'daytime'
]
#문자열
keywords = ["login", "secure", "update", "verify", "urgent", "invoice", "account",
						 "banking", "free", "gift", "cash", "paypal", "facebook", "apple",
						 "amazon", "password", "admin"]

train_df= pd.read_csv(r'C:\Naq\train_dataset.csv')


#https
train_df['check_https'] = train_df['URL'].apply(ExistenceBased.check_https)


#문자열
train_df['check_keyword'] = train_df['URL'].apply(lambda x: ExistenceBased.check_keyword_presence(x,keywords))

#url 길이
length = train_df['URL'].dropna().apply(lambda x: len(str(x))) 
url_avg = length.mean()
url_std = length.std()


train_df['urllength'] =train_df['URL'].apply(lambda x: LengthBased.check_length(x,url_avg,url_std))


#특수문자 개수
schar_count =train_df['URL'].apply(lambda x: CountBased.counting_specialchar(x))
schar_avg = schar_count.mean()
schar_std = schar_count.std()

train_df['countspecialchar'] = schar_count.apply(lambda x: CountBased.check_count_level(x,schar_avg,schar_std))


#숫자 개수
num_count = train_df['URL'].apply(lambda x: CountBased.extract_num(x))
num_avg = num_count.mean()
num_std = num_count.std()

train_df['countnum'] = num_count.apply(lambda x:CountBased.check_count_level(x, num_avg, num_std))

#문자 개수
letter_count = train_df['URL'].apply(lambda x: CountBased.extract_letter(x))
letter_avg = letter_count.mean()
letter_std = letter_count.std()

train_df['countletter'] = letter_count.apply(lambda x: CountBased.check_count_level(x,letter_avg,letter_std))



#SOA 레코드 및 네임서버(NS) 정보를 추출하여 비정상적인 특징을 분석

train_df[['ttl', 'ns_match', 'dns_query_success', 'DNS_mal']] = train_df['URL'].apply(lambda x:pd.Series(DNS.get_dns_features_and_judge(x)))



#일수기반
domain_Day = train_df['URL'].apply(DaysBased.extract_domain)

whois_df = domain_Day.apply(lambda x:DaysBased.extract_domain_dates(x)).apply(pd.Series)


thresholds = DaysBased.compute_thresholds(whois_df)
train_df['daytime'] = whois_df.apply(lambda row: DaysBased.label_by_thresholds(row,thresholds),axis =1)


train_df.to_csv(r"C:\Naq\module_0502_dataset.csv", index = False)


X_train = train_df[feature_columns]
y_train = train_df['is_malicious']  # 타겟 컬럼


#테스트
test_df = pd.read_csv(r'C:\Naq\test_dataset.csv')


test_df['check_https'] = test_df['URL'].apply(ExistenceBased.check_https)
test_df['check_keyword'] = test_df['URL'].apply(lambda x: ExistenceBased.check_keyword_presence(x, keywords))
test_df['urllength'] = test_df['URL'].apply(lambda x: LengthBased.check_length(x, url_avg, url_std))

schar_count_test = test_df['URL'].apply(CountBased.counting_specialchar)
test_df['countspecialchar'] = schar_count_test.apply(lambda x: CountBased.check_count_level(x, schar_avg, schar_std))

num_count_test = test_df['URL'].apply(CountBased.extract_num)
test_df['countnum'] = num_count_test.apply(lambda x: CountBased.check_count_level(x, num_avg, num_std))

letter_count_test = test_df['URL'].apply(CountBased.extract_letter)
test_df['countletter'] = letter_count_test.apply(lambda x: CountBased.check_count_level(x, letter_avg, letter_std))

test_df[['ttl', 'ns_match', 'dns_query_success', 'DNS_mal']] = test_df['URL'].apply(lambda x: pd.Series(DNS.get_dns_features_and_judge(x)))

domain_Day_test = test_df['URL'].apply(DaysBased.extract_domain)
whois_df_test = domain_Day_test.apply(lambda x: DaysBased.extract_domain_dates(x)).apply(pd.Series)
test_df['daytime'] = whois_df_test.apply(lambda row: DaysBased.label_by_thresholds(row, thresholds), axis=1)

X_test = test_df[feature_columns].fillna(-1)
y_test = test_df['is_malicious']



# 🔹 Random Forest 학습
rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
rf_model.fit(X_train, y_train)
rf_pred = rf_model.predict(X_test)

print("✅ [Random Forest]")
print("Accuracy:", accuracy_score(y_test, rf_pred))
print(classification_report(y_test, rf_pred))

# 저장
joblib.dump(rf_model, "0502rf_model.pkl")


# 🔹 XGBoost 학습
xgb_model = XGBClassifier(n_estimators=100, max_depth=5, learning_rate=0.1, use_label_encoder=False, eval_metric='logloss', random_state=42)
xgb_model.fit(X_train, y_train)
xgb_pred = xgb_model.predict(X_test)

print("✅ [XGBoost]")
print("Accuracy:", accuracy_score(y_test, xgb_pred))
print(classification_report(y_test, xgb_pred))

# 저장
joblib.dump(xgb_model, "0502xgb_model.pkl")


