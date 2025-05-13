import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import csv
import pandas as pd
import re
from urllib.parse import urljoin

# CSV 파일에서 도메인 불러오기
file_path = 'C:/Users/user/졸업/0513_tranco.csv'
df = pd.read_csv(file_path)

# 🔹 첫 번째 컬럼에서 전체 도메인 가져오기 (NaN 제거)
domains = df.iloc[:, 1].dropna().tolist()
print(f"✅ 총 {len(domains)}개의 도메인을 가져왔습니다!")

# ✅ 크롤링한 URL 저장 리스트
all_urls = []

# 🔹 1. 올바른 URL 찾기 (https / http / www 자동 탐색)
def get_valid_base_url(domain):
    url_patterns = [
        f"https://{domain}",
        f"http://{domain}",
        f"https://www.{domain}",
        f"http://www.{domain}"
    ]
    for url in url_patterns:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return url  # 유효한 URL 반환
        except Exception:  # 모든 예외를 잡아 URL 파싱 오류 등도 처리
            continue
    return None  # 유효한 URL이 없는 경우

# 🔹 2. 사이트맵에서 첫 번째 URL 가져오기
def get_sitemap_urls(base_url):
    sitemap_url = urljoin(base_url, "sitemap.xml")
    try:
        response = requests.get(sitemap_url, timeout=5)
        if response.status_code == 200:
            try:
                root = ET.fromstring(response.text)
                urls = [elem.text for elem in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
                return urls[:1]
            except ET.ParseError:
                print(f"⚠️ {base_url} - XML 파싱 오류 발생!")
    except Exception:
        pass
    return []

# 🔹 3. 홈페이지에서 내부 링크 1개 크롤링
def crawl_internal_links(base_url):
    try:
        response = requests.get(base_url, timeout=5)
        soup = BeautifulSoup(response.text, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            if href.startswith("http") and base_url in href:
                links.add(href)
            elif href.startswith("/"):
                full_url = urljoin(base_url, href)
                links.add(full_url)
        return list(links)[:1]  # 3개만 반환
    except Exception:
        return []

# 🔹 4. 도메인별 크롤링 실행
for domain in domains:
    # 도메인 앞뒤 공백 제거 후, 선행하는 모든 점(.) 제거
    cleaned_domain = re.sub(r'^\.+', '', domain.strip())
    
    base_url = get_valid_base_url(cleaned_domain)  # 올바른 URL 찾기
    if not base_url:
        print(f"❌ {cleaned_domain}에서 유효한 URL을 찾을 수 없음")
        continue

    print(f"✅ {cleaned_domain} → {base_url}에서 URL 수집 시작")
    
    # 사이트맵에서 URL 추출, 없으면 내부 링크 크롤링
    urls = get_sitemap_urls(base_url)
    if not urls:
        urls = crawl_internal_links(base_url)
    
    if urls:  # 수집된 URL이 도메인과 함께 리스트에 추가
        all_urls.append(urls[0])
        all_urls.append((cleaned_domain, urls[0]))

# 🔹 5. 수집된 URL을 CSV 파일로 저장
csv_filename = "C:/Users/user/졸업/0513_normal_data.csv"
with open(csv_filename, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["Domain", "URL","정상값"])
    
    for domain, url in all_urls:
        writer.writerow([domain, url,0])   

print(f" 총 {len(all_urls)}개의 URL을 {csv_filename}에 저장 완료!")