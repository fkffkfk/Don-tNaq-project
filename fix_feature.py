import pandas as pd
import dns.resolver
import dns.exception
import urllib.parse
from functools import lru_cache
import xml.etree.ElementTree as ET
import string
import re

    #개수기반
    ###개수기반(특수문자,숫자,문자)### 
class CountBased:
    @staticmethod
    def check_count_level(count, avg, std,threshold=1.0):
        if pd.isna(count):
            return None

        lower = avg - std * threshold
        upper = avg + std * threshold
        
        return 1 if count < lower or count > upper else 0 

    @staticmethod
    def counting_specialchar (url):
        if pd.isna(url):
            return None
        return sum (1 for char in str(url) if char in string.punctuation)
    
    
    @staticmethod
    def extract_num(url):
        if pd.isna(url):
            return None
        return sum(n.isdigit() for n in str(url))
    
    
    @staticmethod
    def extract_letter(url):
        if pd.isna(url):
            return None
        return sum(c.isalpha() for c in str(url))
        

"""###존재기반(문자열)###
class ExistenceBased:
    
        
    @staticmethod
    #문자열 포함 여부
    def check_keyword_presence(url, keyword_list):
        url_lower = str(url).lower()  # NaN 방지 및 대소문자 무시
        for keyword in keyword_list:
            if keyword in url_lower:
                return 1  # 특정 키워드 포함 시 1
        return 0  # 포함되지 않으면 0

    


###일수기반###
class DaysBased:
    #도메인 주소가 ip주소인 경우 제외
    @staticmethod
    def is_ip_url(url):
        ip_pattern = r'^https?://\d{1,3}(\.\d{1,3}){3}'
        return bool(re.match(ip_pattern, str(url)))

    
    #도메인 추출 함수
    @staticmethod
    @lru_cache(maxsize=128)
    def extract_domain(url):
        try:
            if pd.isna(url):
                return None
            url = url.strip()

            #ip 주소인 경우는 도메인 없음으로 처리
            if DaysBased.is_ip_url(url):
                print(f"도메인 추출 무시됨 (IP 주소): {url}")
                return None
            

            extracted = tldextract.extract(url)
            # 유효한 도메인 판별: domain과 suffix가 반드시 있어야 함
            if extracted.domain and extracted.suffix:
                return f"{extracted.domain}.{extracted.suffix}"
            else:
                return None

        except Exception as e:
            print(f"도메인 추출 실패 ({url}): {e}")
            return None
        
    

###DNS###
class DNS:
    @staticmethod
    #DNS특징추출함수
    def get_dns_features_and_judge(url):
        DNS_mal = None
        try:
            # 도메인 추출
            domain = DaysBased.extract_domain(url)

            # SOA 레코드 조회
            soa_answer = dns.resolver.resolve(domain, 'SOA')
            ttl = soa_answer.rrset.ttl

            # NS 레코드 조회
            ns_answer = dns.resolver.resolve(domain, 'NS')
            ns_servers = [ns.to_text() for ns in ns_answer]
            primary_ns = ns_servers[0] if ns_servers else ""

            # NS에 도메인 이름이 포함되는지 확인
            ns_match = 1 if domain.lower() in primary_ns.lower() else 0
            dns_success = 1

        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            ttl = -1
            ns_match = -1
            dns_success = 0
            DNS_mal = 1  
        except Exception as e:
            print(f"⚠️ 기타 오류 발생: {e}")
            ttl = -1
            ns_match = -1
            dns_success = 0
            DNS_mal = 1  

        # 악성 여부 판단
        if(DNS_mal==1):
            pass
        else:
            if (ttl == 86400 and ns_match == 0) or \
            (ttl == 86400 and dns_success == 0) or \
            (ns_match == 0 and dns_success == 0) or \
            (ttl == 86400 and ns_match == 0 and dns_success == 0): DNS_mal = 1
            else: DNS_mal = 0
            
        return pd.Series([ttl, ns_match, dns_success, DNS_mal])
    """
    
