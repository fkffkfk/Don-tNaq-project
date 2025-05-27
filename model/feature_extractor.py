import pandas as pd
from feature_module import ExistenceBased, LengthBased, CountBased, DaysBased, DNS

class FeatureExtractor:
    def __init__(self,url_length_lower,url_length_upper, schar_avg, schar_std,
                 num_avg, num_std, letter_avg, letter_std,
                 thresholds, keywords):
        self.url_length_lower = url_length_lower
        self.url_length_upper = url_length_upper
        self.schar_avg = schar_avg
        self.schar_std = schar_std
        self.num_avg = num_avg
        self.num_std = num_std
        self.letter_avg = letter_avg
        self.letter_std = letter_std
        self.thresholds = thresholds
        self.keywords = keywords

        self.feature_columns = [
            'check_https', 'check_keyword', 'urllength',
            'countspecialchar', 'countnum', 'countletter',
            'ttl', 'ns_match', 'dns_query_success', 'DNS_mal',
            'daytime'
        ]

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()

        df['check_https'] = df['URL'].apply(ExistenceBased.check_https)
        df['check_keyword'] = df['URL'].apply(
            lambda x: ExistenceBased.check_keyword_presence(x, self.keywords)
        )
        df['urllength'] = df['URL'].apply(
            lambda x: LengthBased.check_length(x, self.url_length_lower, self.url_length_upper)
        )

        schar_count = df['URL'].apply(CountBased.counting_specialchar)
        df['countspecialchar'] = schar_count.apply(
            lambda x: CountBased.check_count_level(x, self.schar_avg, self.schar_std)
        )

        num_count = df['URL'].apply(CountBased.extract_num)
        df['countnum'] = num_count.apply(
            lambda x: CountBased.check_count_level(x, self.num_avg, self.num_std)
        )

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

        return df[self.feature_columns].fillna(-1)