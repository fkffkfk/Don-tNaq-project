import pandas as pd
import random
from feature_module import ExistenceBased,LengthBased,CountBased,DaysBased,DNS

df = pd.read_csv(r'C:\grdu_project\model_training\train_dataset.csv')


#https
df['check_https'] = df['URL'].apply(ExistenceBased.check_https)

#문자열
keywords = ["login", "secure", "update", "verify", "urgent", "invoice", "account",
						 "banking", "free", "gift", "cash", "paypal", "facebook", "apple",
						 "amazon", "password", "admin"]
df['check_keyword'] = df['URL'].apply(lambda x: ExistenceBased.check_keyword_presence(x,keywords))

#url 길이
length = df['URL'].dropna().apply(lambda x: len(str(x))) 
url_avg = length.mean()
url_std = length.std()


df['urllength'] =df['URL'].apply(lambda x: LengthBased.check_length(x,url_avg,url_std))


#특수문자 개수
schar_count =df['URL'].apply(lambda x: CountBased.counting_specialchar(x))
schar_avg = schar_count.mean()
schar_std = schar_count.std()

df['countspecialchar'] = schar_count.apply(lambda x: CountBased.check_count_level(x,schar_avg,schar_std))


#숫자 개수
num_count = df['URL'].apply(lambda x: CountBased.extract_num(x))
num_avg = num_count.mean()
num_std = num_count.std()

df['countnum'] = num_count.apply(lambda x:CountBased.check_count_level(x, num_avg, num_std))

#문자 개수
letter_count = df['URL'].apply(lambda x: CountBased.extract_letter(x))
letter_avg = letter_count.mean()
letter_std = letter_count.std()

df['countletter'] = letter_count.apply(lambda x: CountBased.check_count_level(x,letter_avg,letter_std))



#SOA 레코드 및 네임서버(NS) 정보를 추출하여 비정상적인 특징을 분석

df[['ttl', 'ns_match', 'dns_query_success', 'DNS_mal']] = df['URL'].apply(lambda x:pd.Series(DNS.get_dns_features_and_judge(x)))



#일수기반
domain_Day = df['URL'].apply(DaysBased.extract_domain)

whois_df = domain_Day.apply(lambda x:DaysBased.extract_domain_dates(x)).apply(pd.Series)


thresholds = DaysBased.compute_thresholds(whois_df)
df['daytime'] = whois_df.apply(lambda row: DaysBased.label_by_thresholds(row,thresholds),axis =1)


df.to_csv(r"C:\grdu_project\model_training\module_train_dataset.csv", index = False)

