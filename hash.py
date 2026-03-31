# hash_password.py

import bcrypt

raw_password = "admin1"  # 원하는 비밀번호 입력
hashed_pw = bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt())

print("복사할 bcrypt 해시:", hashed_pw.decode())
