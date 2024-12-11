# utils.py
import csv
import os
from datetime import datetime
from pathlib import Path

def ensure_directory_exists(directory: str):
    """디렉토리가 존재하지 않으면 생성"""
    Path(directory).mkdir(parents=True, exist_ok=True)

def save_to_csv(data: dict, directory: str = "txtfiles"):
    """상담 결과를 CSV 파일로 저장"""
    ensure_directory_exists(directory)
    
    filename = f"{directory}/counseling_log_{datetime.now().strftime('%Y%m')}.csv"
    file_exists = os.path.exists(filename)
    
    row_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": data.get("source", "console"),  # 상담 출처 (console 또는 email)
        "email": data.get("email", ""),  # 이메일 주소 (이메일로 받은 경우)
        "original_concern": data["gomin_result"]["STEP-1"],
        "concern_summary": data["gomin_result"]["STEP-3"]["요약"],
        "lacking_aspect": data["gomin_result"]["STEP-4"]["부족함"],
        "concept": data["gomin_result"]["STEP-4"]["하위개념"],
        "concept_reason": data["gomin_result"]["STEP-4"]["이유"],
        "selected_quote": data["advice_result"]["STEP-2"],
        "quote_reason": data["advice_result"]["STEP-3"],
        "advice": data["advice_result"]["STEP-4"],
        "analysis_time": data["time1"],
        "advice_time": data["time2"]
    }
    
    with open(filename, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=row_data.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_data)

def process_and_save_concern(processor, concern: str, email: str = "", source: str = "console"):
    """고민 처리 및 저장"""
    print("\n고민을 분석중입니다...")
    gomin_result, time1 = processor.process_gomin(concern)
    
    if not gomin_result["STEP-2"]:
        print("입력하신 내용이 고민이 아닌 것 같습니다.")
        return None
            
    print(f"분석 시간: {time1:.2f}초")
    print("\n조언을 생성중입니다...")
    
    advice_result, time2 = processor.generate_advice(gomin_result)
    print(f"생성 시간: {time2:.2f}초")
    
    # 결과 저장
    data = {
        "source": source,
        "email": email,
        "gomin_result": gomin_result,
        "advice_result": advice_result,
        "time1": time1,
        "time2": time2
    }
    save_to_csv(data)
    
    # 결과 출력
    print("\n=== 분석 결과 ===")
    print(f"고민 요약: {gomin_result['STEP-3']['요약']}")
    print(f"부족한 점: {gomin_result['STEP-4']['부족함']}")
    print(f"보완할 개념: {gomin_result['STEP-4']['하위개념']}")
    
    print("\n=== 조언 ===")
    print(f"선택된 논어 구절: {advice_result['STEP-2']}")
    print(f"조언: {advice_result['STEP-4']}")
    
    return advice_result