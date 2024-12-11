# send_mail.py
import imaplib
import email
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from datetime import datetime, timedelta
from jinja2 import Environment, FileSystemLoader
import openai
import os
from dotenv import load_dotenv
from gongja import GongjaProcessor
from dataclasses import dataclass
from utils import process_and_save_concern

@dataclass
class EmailConfig:
    """이메일 설정을 관리하는 클래스"""
    IMAP_SERVER: str = None
    SMTP_SERVER: str = None
    EMAIL_ACCOUNT: str = None
    PASSWORD: str = None
    TEMPLATE_PATH: str = './template'
    TEMPLATE_FILE: str = 'newsletter.html'

    @classmethod
    def from_env(cls):
        """환경 변수에서 설정 로드"""
        return cls(
            IMAP_SERVER=os.getenv('IMAP_SERVER'),
            SMTP_SERVER=os.getenv('SMTP_SERVER'),
            EMAIL_ACCOUNT=os.getenv('EMAIL_ACCOUNT'),
            PASSWORD=os.getenv('EMAIL_PASSWORD'),
            TEMPLATE_PATH='./template',
            TEMPLATE_FILE='newsletter.html'
        )

class EmailProcessor:
    """이메일 처리를 담당하는 클래스"""
    def __init__(self, config: EmailConfig, gongja_processor: GongjaProcessor):
        self.config = config
        self.gongja_processor = gongja_processor
        self.env = Environment(loader=FileSystemLoader(config.TEMPLATE_PATH))
        
    @staticmethod
    def decode_subject(subject: str) -> str:
        """이메일 제목 디코딩"""
        decoded_fragments = decode_header(subject)
        decoded_subject = ''
        for fragment, encoding in decoded_fragments:
            if isinstance(fragment, bytes):
                if encoding:
                    decoded_subject += fragment.decode(encoding)
                else:
                    decoded_subject += fragment.decode('utf-8')
            else:
                decoded_subject += fragment
        return decoded_subject

    def get_email_body(self, msg: email.message.Message) -> str:
        """이메일 본문 추출"""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))

                if "attachment" not in content_disposition:
                    if content_type in ["text/plain", "text/html"]:
                        return part.get_payload(decode=True).decode()
        else:
            content_type = msg.get_content_type()
            if content_type in ["text/plain", "text/html"]:
                return msg.get_payload(decode=True).decode()
        return ""

    def send_auto_reply(self, to_email: str, original_subject: str, custom_message: str, original_content: str):
        """자동 답장 발송"""
        reply_subject = f"Re: {original_subject}"
        template = self.env.get_template(self.config.TEMPLATE_FILE)
        html_content = template.render(
            gomin_content=original_content,
            message=custom_message
        )

        msg = MIMEMultipart('alternative')
        msg['From'] = self.config.EMAIL_ACCOUNT
        msg['To'] = to_email
        msg['Subject'] = reply_subject
        msg.attach(MIMEText(html_content, 'html'))

        try:
            with smtplib.SMTP(self.config.SMTP_SERVER, 587) as server:
                server.starttls()
                server.login(self.config.EMAIL_ACCOUNT, self.config.PASSWORD)
                server.sendmail(self.config.EMAIL_ACCOUNT, to_email, msg.as_string())
            print(f"자동 답장 발송 성공: {to_email}")
        except Exception as e:
            print(f"자동 답장 발송 실패: {e}")

    def process_single_email(self, msg: email.message.Message):
        """단일 이메일 처리"""
        from_email = email.utils.parseaddr(msg['From'])[1]
        subject = self.decode_subject(msg['Subject'])
        print(f"From: {from_email}, Subject: {subject}")

        if "고민" in subject.lower() or "상담" in subject.lower():
            print("조건에 맞는 이메일을 찾았습니다.")
            email_body = self.get_email_body(msg)
            print(f"Body: {email_body}")

            advice_result = process_and_save_concern(
                processor=self.gongja_processor,
                concern=email_body,
                email=from_email,
                source="email"
            )
            
            if advice_result:
                self.send_auto_reply(
                    from_email, 
                    subject, 
                    advice_result["STEP-4"],
                    email_body
                )
                print("자동 답장에 성공했습니다.")
            else:
                print("고민 처리에 실패했습니다.")
        else:
            print("조건에 맞지 않는 이메일입니다.")
            print("자동 답장을 보류합니다.")

    def read_emails(self):
        """이메일 읽기 및 처리"""
        with imaplib.IMAP4_SSL(self.config.IMAP_SERVER) as mail:
            mail.login(self.config.EMAIL_ACCOUNT, self.config.PASSWORD)
            mail.select('inbox')

            date = (datetime.now() - timedelta(1)).strftime("%d-%b-%Y")
            result, data = mail.search(None, f'(SINCE "{date}")')

            if result == "OK":
                for num in data[0].split():
                    result, data = mail.fetch(num, '(RFC822)')
                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    self.process_single_email(msg)

def setup_environment():
    """환경 설정 초기화"""
    load_dotenv()
    
    # OpenAI API 키 설정
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    # 이메일 설정 검증
    required_env_vars = [
        "EMAIL_ACCOUNT", 
        "EMAIL_PASSWORD",
        "IMAP_SERVER",
        "SMTP_SERVER"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")

def main():
    """메인 실행 함수"""
    try:
        setup_environment()
        config = EmailConfig.from_env()
        gongja_processor = GongjaProcessor()
        email_processor = EmailProcessor(config, gongja_processor)
        email_processor.read_emails()
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()