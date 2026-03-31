import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

def send_verification_email(
    *, smtp_host: str, smtp_port: int,
    smtp_user: str, smtp_pass: str,
    mail_from: str, mail_from_name: str,
    to_email: str, verify_url: str
):
    """인증 메일 발송(465 SSL / 587 TLS 자동 분기)"""

    msg = EmailMessage()
    msg['Subject'] = "[낚지마] 이메일 인증을 완료해주세요"
    msg['From'] = formataddr((mail_from_name, mail_from))
    msg['To'] = to_email

    # 텍스트/HTML 멀티파트
    msg.set_content(
        f"아래 링크를 클릭하여 이메일 인증을 완료해주세요.\n\n{verify_url}\n"
        "본인이 요청하지 않았다면 이 메일은 무시하셔도 됩니다."
    )

    msg.add_alternative(f"""\
<!doctype html>
<html>
  <body style="font-family:system-ui, -apple-system, Segoe UI, Roboto, Apple SD Gothic Neo;">
    <div style="max-width:560px;margin:24px auto;padding:16px;border:1px solid #e5e7eb;border-radius:10px;">
      <h2 style="margin:0 0 12px 0;">이메일 인증을 완료해주세요</h2>
      <p style="margin:0 0 16px 0;">아래 버튼을 눌러 30분 내에 인증을 완료하세요.</p>
      <p style="margin:24px 0;">
        <a href="{verify_url}"
           style="display:inline-block;padding:10px 16px;border-radius:8px;background:#2d6cdf;color:#fff;
                  text-decoration:none;font-weight:600;">
          이메일 인증하기
        </a>
      </p>
      <p style="color:#6b7280;font-size:14px;">
        버튼이 동작하지 않으면 다음 주소를 브라우저에 붙여넣으세요:<br>
        <span style="word-break:break-all;">{verify_url}</span>
      </p>
      <hr style="border:none;border-top:1px solid #f1f5f9;margin:16px 0;">
      <p style="color:#94a3b8;font-size:12px;margin:0;">
        본인이 요청하지 않았다면 이 메일은 무시하셔도 됩니다.
      </p>
    </div>
  </body>
</html>
""", subtype="html")

    # SSL(465) 또는 TLS(587) 자동 분기
    if smtp_port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as s:
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)
    else:
        context = ssl.create_default_context()
        with smtplib.SMTP(smtp_host, smtp_port) as s:
            s.ehlo()
            s.starttls(context=context)
            s.ehlo()
            s.login(smtp_user, smtp_pass)
            s.send_message(msg)



