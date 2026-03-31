import pandas as pd
import dns.resolver
import dns.exception
import urllib.parse
from functools import lru_cache
import xml.etree.ElementTree as ET
import tldextract
from datetime import datetime
import logging
import string
import re
import numpy as np
import ssl
import socket
from datetime import datetime, timezone
from urllib.parse import urlparse
import idna
from cryptography import x509
from cryptography.hazmat.backends import default_backend


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
            return 0 #정상
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
        elif avg - std <= count <= avg + std:
            return 0  # 정상
        else:
            return 1 
        
    @staticmethod
    def check_count_level1(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std*0.1:
            return 1  # 악성
        elif avg - std*0.1 <= count <= avg + std*0.1:
            return 0  # 정상
        else:
            return 1 
    @staticmethod
    def check_count_level2(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std*0.2:
            return 1  # 악성
        elif avg - std*0.2 <= count <= avg + std*0.2:
            return 0  # 정상
        else:
            return 1 
    @staticmethod
    def check_count_level3(count, avg, std):
        if pd.isna(count):
            return None

        if count < avg - std*0.3:
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


    

###DNS###
class DNS:
    @staticmethod
    @lru_cache(maxsize=2048)
    #DNS특징추출함수
    def get_dns_features_and_judge(domain):
        DNS_mal = None
        try:
            # 도메인 추출 생략
            #domain = DaysBased.extract_domain(url)

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
    

#SSL기반
class SSL:
    @staticmethod
    def extract_ssl_features_advanced(url):
        try:
            hostname = urlparse(url).hostname
            if not hostname:
                raise ValueError('Invalid URL structure')
            hostname = idna.encode(hostname).decode('ascii')
            port = 443

            context = ssl.create_default_context()

            with socket.create_connection((hostname, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    der_cert = ssock.getpeercert(binary_form=True)
                    tls_version = ssock.version() or "unknown"

            cert = x509.load_der_x509_certificate(der_cert, backend=default_backend())

            # CN 정보
            issuer_cn = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value \
                if cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME) else ""
            subject_cn = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)[0].value \
                if cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME) else ""

            now = datetime.now(timezone.utc)
            not_before = cert.not_valid_before_utc
            not_after = cert.not_valid_after_utc
            cert_valid_days = (not_after - not_before).days

            # SAN 필드
            try:
                ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
                san_dns_names = ext.value.get_values_for_type(x509.DNSName)
                san_count = len(san_dns_names)
                hostname_in_san = hostname in san_dns_names
            except:
                san_dns_names = []
                san_count = 0
                hostname_in_san = False

            # CN 또는 SAN 중 하나라도 일치하면 정상
            domain_mismatch = not (hostname == subject_cn or hostname_in_san)

            # 키 알고리즘
            pubkey = cert.public_key()
            if hasattr(pubkey, 'key_size'):
                key_bits = pubkey.key_size
                key_algo = f"RSA-{key_bits}" if 'rsa' in pubkey.__class__.__name__.lower() else f"{pubkey.__class__.__name__}-{key_bits}"
            else:
                key_algo = "UNKNOWN"

            return {
                'is_untrusted_ca': int(not any(x in issuer_cn for x in ["Let's Encrypt", "Google", "DigiCert", "GlobalSign",
                                                                "Amazon", "Microsoft", "GoDaddy", "Sectigo", "GeoTrust",
                                                                "한국전자인증", "한국정보인증"])),
                'is_weak_protocol': int(tls_version.lower() in ['sslv3', 'tlsv1', 'tlsv1.1']),
                'is_weak_key_algo': int(key_algo.startswith('RSA-') and int(key_algo.split('-')[1]) <= 1024),
                'is_short_lived_cert': int(cert_valid_days < 7),
                'is_expired': int(now > not_after),
                'domain_cn_mismatch': int(domain_mismatch),
                'is_self_signed': int(subject_cn == issuer_cn),
                'san_count_high': int(san_count > 50)
            }

        except Exception:
            # SSL 오류 발생 시 모든 특징을 '1' (악성)으로 간주
            return {
                'is_untrusted_ca': 1,
                'is_weak_protocol': 1,
                'is_weak_key_algo': 1,
                'is_short_lived_cert': 1,
                'is_expired': 1,
                'domain_cn_mismatch': 1,
                'is_self_signed': 1,
                'san_count_high': 1
            }



    





