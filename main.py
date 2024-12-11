# main.py
import os
from dotenv import load_dotenv
import openai
from config import Config
from gongja import GongjaProcessor
from send_mail import EmailConfig, EmailProcessor
from utils import process_and_save_concern
from gomins import worries
import argparse

def setup_environment():
    """환경 설정 초기화"""
    load_dotenv()
    config = Config()
    config.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    # 이메일 관련 환경 변수 검증
    required_env_vars = [
        "EMAIL_ACCOUNT", 
        "EMAIL_PASSWORD",
        "IMAP_SERVER",
        "SMTP_SERVER"
    ]
    
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(f"다음 환경 변수가 설정되지 않았습니다: {', '.join(missing_vars)}")
    
    openai.api_key = config.OPENAI_API_KEY
    return config

def display_worry_categories():
    """고민 카테고리 출력"""
    print("\n=== 고민 카테고리 ===")
    for idx, category in enumerate(worries.keys(), 1):
        print(f"{idx}. {category}")
    return list(worries.keys())

def display_worries_in_category(category):
    """선택된 카테고리의 고민들 출력"""
    print(f"\n=== {category} 관련 고민들 ===")
    for idx, worry in enumerate(worries[category], 1):
        # 긴 고민 텍스트를 줄여서 표시
        short_worry = worry[:50] + "..." if len(worry) > 50 else worry
        print(f"{idx}. {short_worry}")
    return worries[category]

def get_valid_input(max_num: int, prompt: str) -> int:
    """유효한 숫자 입력 받기"""
    while True:
        try:
            num = int(input(prompt))
            if 1 <= num <= max_num:
                return num
            print(f"1부터 {max_num} 사이의 숫자를 입력해주세요.")
        except ValueError:
            print("유효한 숫자를 입력해주세요.")

def select_predefined_worry():
    """미리 정의된 고민 선택"""
    # 카테고리 선택
    categories = display_worry_categories()
    category_num = get_valid_input(
        len(categories),
        "\n카테고리 번호를 선택하세요: "
    )
    selected_category = categories[category_num - 1]

    # 선택된 카테고리에서 고민 선택
    worries_list = display_worries_in_category(selected_category)
    worry_num = get_valid_input(
        len(worries_list),
        "\n고민 번호를 선택하세요: "
    )
    
    return worries_list[worry_num - 1]

def process_console_input(processor: GongjaProcessor):
    """콘솔 입력 처리"""
    print("\n고민 상담을 시작합니다.")
    print("1: 직접 고민 입력하기")
    print("2: 미리 정의된 고민에서 선택하기")
    print("종료하려면 'quit' 또는 'exit'를 입력하세요.")
    
    while True:
        choice = input("\n선택해주세요 (1 또는 2): ").strip()
        
        if choice.lower() in ['quit', 'exit']:
            print("상담을 종료합니다.")
            break
        
        if choice not in ['1', '2']:
            print("1 또는 2를 선택해주세요.")
            continue
            
        if choice == '1':
            user_input = input("\n고민을 입력하세요: ").strip()
            if not user_input:
                print("고민을 입력해주세요.")
                continue
        else:
            user_input = select_predefined_worry()
            print("\n선택한 고민:", user_input)
        
        process_and_save_concern(processor, user_input)

def process_email(processor: GongjaProcessor):
    """이메일 처리"""
    try:
        print("이메일 처리를 시작합니다...")
        email_config = EmailConfig.from_env()
        email_processor = EmailProcessor(email_config, processor)
        email_processor.read_emails()
        print("이메일 처리가 완료되었습니다.")
    except Exception as e:
        print(f"이메일 처리 중 오류 발생: {str(e)}")

def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="""
    고민 상담 프로그램
    
    실행 모드:
    - console: 터미널에서 직접 고민을 입력하거나 미리 정의된 고민을 선택합니다.
    - email: 이메일로 받은 고민을 자동으로 처리하고 답장합니다.
    """)
    
    parser.add_argument('--mode', 
                       choices=['console', 'email'],
                       default='console', 
                       help='실행 모드 선택 (console 또는 email)')
    
    args = parser.parse_args()
    
    try:
        config = setup_environment()
        processor = GongjaProcessor()
        
        if args.mode == 'console':
            process_console_input(processor)
        else:  # email mode
            process_email(processor)
            
    except Exception as e:
        print(f"오류가 발생했습니다: {str(e)}")

if __name__ == "__main__":
    main()