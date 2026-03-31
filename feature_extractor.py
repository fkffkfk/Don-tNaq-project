import pandas as pd
from urllib.parse import urlparse
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS, SSL

class FeatureExtractor:
    def __init__(self, url_avg, url_std, schar_avg, schar_std,
             letter_avg, letter_std, keywords):
        
        self.url_avg = url_avg
        self.url_std = url_std
        self.schar_avg = schar_avg
        self.schar_std = schar_std
        self.letter_avg = letter_avg
        self.letter_std = letter_std
        self.keywords = keywords


        self.feature_columns = [
            'check_https', 'check_keyword', 
            'url_length', 'specialchar_count',
            'countletter',
            'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
            'is_untrusted_ca','is_weak_protocol','is_weak_key_algo','is_short_lived_cert','is_expired',
            'domain_cn_mismatch','is_self_signed','san_count_high'
        ]

    def _ensure_domain(self, df: pd.DataFrame) -> pd.DataFrame:
        if 'domain' not in df.columns:
            df['domain'] = df['URL'].apply(DaysBased.extract_domain)
        return df
    

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self._ensure_domain(df)

        df['check_https'] = df['URL'].apply(ExistenceBased.check_https)
        df['check_keyword'] = df['URL'].apply(
            lambda x: ExistenceBased.check_keyword_presence(x, self.keywords)
        )
    
        #길이
        df['url_length'] = df['URL'].apply(
            lambda x: LengthBased.check_length(x, self.url_avg, self.url_std)
        )

        # 특수문자
        schar_count = df['URL'].apply(CountBased.counting_specialchar)
        df['specialchar_count'] = df['URL'].apply(
            lambda x: CountBased.check_count_level(
                CountBased.counting_specialchar(x),
                self.schar_avg, self.schar_std
            )
        )
        #문자 
        letter_count = df['URL'].apply(CountBased.extract_letter)
        df['countletter'] = letter_count.apply(
            lambda x: CountBased.check_count_level(x, self.letter_avg, self.letter_std)
        )
        
        df[['ttl', 'ns_match', 'dns_query_success', 'DNS_mal']] = df['domain'].apply(
            lambda x: DNS.get_dns_features_and_judge(x)
        )
        
        
        #SSL
        ssl_df = df['URL'].apply(SSL.extract_ssl_features_advanced)
        ssl_df = pd.DataFrame(ssl_df.tolist())
        df = pd.concat([df, ssl_df], axis=1)


        return df[self.feature_columns].fillna(-1)
    
