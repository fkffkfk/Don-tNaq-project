import pandas as pd
import dns.resolver
import dns.exception
import urllib.parse
from functools import lru_cache
import xml.etree.ElementTree as ET
import tldextract
import whois
from datetime import datetime
import logging
import string
import re


###존재기반(HTTPS, 문자열)###
class ExistenceBased:
    @staticmethod
    def check_https(url):
        if pd.isna(url): #Nan인 경우
            return None
        url = str(url)
        if url[:5] == 'https':
            return 0
        else:
            return 1 #악성
        
    @staticmethod
    #문자열 포함 여부
    def check_keyword_presence(url, keyword_list):
        url_lower = str(url).lower()  # NaN 방지 및 대소문자 무시
        for keyword in keyword_list:
            if keyword in url_lower:
                return 1  # 특정 키워드 포함 시 1
        return 0  # 포함되지 않으면 0

    
###URL길이기반###
class LengthBased:
    @staticmethod
    def check_length(url,url_avg,url_std):
        if pd.isna(url):
            return None
        
        length  = len(str(url))

        if length < url_avg - url_std:
            return 1 #악성, 너무 짧음
        elif url_avg - url_std <= length <= url_avg + url_std:
            return 0 #정상상
        else:
            return 1 #악성, 너무 김
        
        
    @staticmethod
    def check_length2(url, lower, upper):
        if pd.isna(url):
            return None
        length = len(str(url))
        return 1 if length < lower or length > upper else 0
    
    
###개수기반(특수문자,숫자,문자)### 
class CountBased:
    @staticmethod
    def check_count_level(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std:
            return 1  # 악성
        elif avg - std*0.1 <= count <= avg + std*0.1:
            return 0  # 정상
        else:
            return 1 
        
    @staticmethod
    def check_count_level1(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std:
            return 1  # 악성
        elif avg - std*0.1 <= count <= avg + std*0.1:
            return 0  # 정상
        else:
            return 1 
    @staticmethod
    def check_count_level2(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std:
            return 1  # 악성
        elif avg - std*0.2 <= count <= avg + std*0.2:
            return 0  # 정상
        else:
            return 1 
    @staticmethod
    def check_count_level3(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std:
            return 1  # 악성
        elif avg - std*0.3 <= count <= avg + std*0.3:
            return 0  # 정상
        else:
            return 1 

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
        
    
    # 날짜 형식 통일 함수 (예외 처리 포함)
    @staticmethod
    def convert_to_datetime(date):
        if isinstance(date, datetime):
            return date
        try:
            return datetime.strptime(str(date), "%Y-%m-%d %H:%M:%S")
        except Exception:
            try:
                return datetime.strptime(str(date), "%Y-%m-%d")
            except Exception:
                return None

    #WHOIS에서 날짜 정보 추출 함수
    @staticmethod
    @lru_cache(maxsize=128)
    def extract_domain_dates(domain_name):
        try:
            whois_info = whois.whois(domain_name)
            creation_date = whois_info.creation_date
            update_date = whois_info.updated_date
            expiration_date = whois_info.expiration_date

            # 리스트 형태일 경우 첫 번째 값 사용
            if isinstance(creation_date, list):
                creation_date = creation_date[0]
            if isinstance(update_date, list):
                update_date = update_date[0]
            if isinstance(expiration_date, list):
                expiration_date = expiration_date[0]

            # datetime으로 변환
            creation_date = DaysBased.convert_to_datetime(creation_date)
            update_date = DaysBased.convert_to_datetime(update_date)
            expiration_date = DaysBased.convert_to_datetime(expiration_date)

            now = datetime.now()
            days_since_creation = (now - creation_date).days if creation_date else None
            days_since_update = (now - update_date).days if update_date else None
            days_until_expiration = (expiration_date - now).days if expiration_date else None

            return {
                "days_since_creation": days_since_creation,
                "days_since_update": days_since_update,
                "days_until_expiration": days_until_expiration
            }

        except Exception as e:
            # WHOIS 정보가 없거나 에러 발생 시
            return {
                "days_since_creation": None,
                "days_since_update": None,
                "days_until_expiration": None
            }

    
        

    # 임계값 계산 함수 (Q1하위25퍼 기준)
    @staticmethod
    def compute_thresholds(df):
        return {
            "days_since_creation": df["days_since_creation"].quantile(0.25),
            "days_since_update": df["days_since_update"].quantile(0.25),
            "days_until_expiration": df["days_until_expiration"].quantile(0.25)
        }

    # 불확실성 반영 + 임계값 기반 분류 함수
    @staticmethod
    def label_by_thresholds(row, thresholds):
        score = 0
        if row['days_since_creation'] is None and row['days_since_update'] is None and row['days_until_expiration'] is None:
            return 2

        if row['days_since_creation'] is not None and row['days_since_creation'] < thresholds['days_since_creation']:
            score += 2
        if row['days_since_update'] is not None and row['days_since_update'] < thresholds['days_since_update']:
            score += 1
        if row['days_until_expiration'] is not None and row['days_until_expiration'] < thresholds['days_until_expiration']:
            score += 1

        # 불확실성 점수 부여 (날짜가 아예 없을 경우)
        if row['days_since_update'] is None:
            score += 1  # 불확실하므로 점수 추가
        

        return 1 if score >= 3 else 0
    

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




    





