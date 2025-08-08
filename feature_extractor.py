import pandas as pd
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS, SSL

class FeatureExtractor:
    def __init__(self, letter_avg, letter_std,
                 thresholds, keywords):
        
       
        self.letter_avg = letter_avg
        self.letter_std = letter_std
        self.thresholds = thresholds
        self.keywords = keywords

        self.feature_columns = [
            'check_https', 'check_keyword', 'countletter',
            'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
            'daytime',
            'is_untrusted_ca','is_weak_protocol','is_weak_key_algo','is_short_lived_cert','is_expired',
            'domain_cn_mismatch','is_self_signed','san_count_high'
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df['check_https'] = df['URL'].apply(ExistenceBased.check_https)
        df['check_keyword'] = df['URL'].apply(
            lambda x: ExistenceBased.check_keyword_presence(x, self.keywords)
        )
      

    

        #문자 
        letter_count = df['URL'].apply(CountBased.extract_letter)
        df['countletter'] = letter_count.apply(
            lambda x: CountBased.check_count_level(x, self.letter_avg, self.letter_std)
        )
        
        df[['ttl', 'ns_match', 'dns_query_success', 'DNS_mal']] = df['URL'].apply(
            lambda x: DNS.get_dns_features_and_judge(x)
        )

        domains = df['URL'].apply(DaysBased.extract_domain)
        whois_info = domains.apply(lambda x: DaysBased.extract_domain_dates(x)).apply(pd.Series)
        df['daytime'] = whois_info.apply(
            lambda row: DaysBased.label_by_thresholds(row, self.thresholds), axis=1
        )

        #SSL
        ssl_df = df['URL'].apply(SSL.extract_ssl_features_advanced)  # 각 URL → dict
        ssl_df = pd.DataFrame(ssl_df.tolist())  # dict → DataFrame (열별 분해)
        df = pd.concat([df, ssl_df], axis=1)  # 원본 df에 병합


        return df[self.feature_columns].fillna(-1)