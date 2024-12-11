import openai
import json
import time
import random
from typing import Dict, Tuple, Any
from pathlib import Path
from gomins import supervised_knowledge

class GPTConfig:
    """GPT 모델 설정을 관리하는 클래스"""
    DEFAULT_SETTINGS = {
        "temperature": 0.8,
        "top_p": 1
    }
    
    GPT_MODELS = {
        "gpt3": "gpt-3.5-turbo",
        "gpt4": "gpt-4-turbo",
        "gpt4o": "gpt-4o",
        "gpt4o-mini": "gpt-4o-mini"
    }
    
    @classmethod
    def get_default_model(cls, model_type: str = "gpt4o-mini") -> str:
        """기본 모델 반환"""
        return cls.GPT_MODELS.get(model_type, cls.GPT_MODELS["gpt4o-mini"])

class GongjaProcessor:
    """고민 상담 처리를 위한 클래스"""
    def __init__(self, knowledge: Dict = supervised_knowledge):
        self.knowledge = knowledge
        self.system_content = "당신은 공자입니다. 공자가 쓸 법한 오래된 현자의 말투를 씁니다. '~하네', '~일세', '~하게'와 같은 말투입니다. 그렇게 말하지만, 당신은 요즘 시대에 아주 좋은 통찰을 주기도 합니다. 제자의 고민을 지혜롭게 해결해주세요."
        self.introduction = self._create_introduction()
        
    def _create_introduction(self) -> str:
        """소개말 생성"""
        return f"""논어의 인(仁)은 {self.knowledge["인의개념"][0]["설명"]}와 같네. 
                  그 하위개념은 {self.knowledge["인의개념"][1]["하위개념"]}라네. 
                  각 하위 개념의 설명은 {self.knowledge["인의하위개념_서예학"]}일세. 
                  인과 하위개념 간 관계는 {self.knowledge["인과하위개념간관계"]}와 같네. 
                  그러므로 논어가 제시하는 바람직한 인간관은 {self.knowledge["바람직한인간관"]}이네. 
                  이러한 논어의 내용을 바탕으로 자네의 고민을 들어주겠네."""
    
    @staticmethod
    def _call_gpt(messages: list, model: str = GPTConfig.get_default_model()) -> Tuple[Dict, float]:
        """GPT API 호출 및 실행 시간 측정"""
        start_time = time.time()
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            **GPTConfig.DEFAULT_SETTINGS
        ).model_dump()
        execution_time = time.time() - start_time
        
        return response, execution_time
    
    @staticmethod
    def _parse_response(response: Dict) -> Dict:
        """GPT 응답을 파싱하여 JSON 형태로 변환"""
        try:
            content = response['choices'][0]['message']['content']
            print(f"원본 content: {content}")
            
            # '<출력 결과>' 마커가 있는 경우 처리
            if '<출력 결과>' in content:
                json_text = content.split('<출력 결과>')[1].strip()
            else:
                json_text = content.strip()
                
            # 코드 블록 마커(```)가 있는 경우 처리
            if json_text.startswith('```'):
                # 첫 번째 줄에서 언어 식별자와 시작 마커 제거
                first_newline = json_text.find('\n')
                if first_newline != -1:
                    json_text = json_text[first_newline:].strip()
                
                # 끝에 있는 코드 블록 마커 제거
                if json_text.endswith('```'):
                    json_text = json_text[:-3].strip()
            
            # 앞뒤 공백, 콜론 제거
            json_text = json_text.strip(': \n')
            
            # JSON 파싱 시도
            try:
                return json.loads(json_text)
            except json.JSONDecodeError as je:
                print(f"JSON 디코딩 오류: {str(je)}")
                print(f"파싱 시도한 텍스트: {json_text}")
                raise
                
        except Exception as e:
            print(f"응답 파싱 중 오류 발생: {str(e)}")
            print(f"원본 응답: {content}")
            raise ValueError("JSON 파싱 실패")
    
    def process_gomin(self, text_gomin: str) -> Tuple[Dict, float]:
        """고민 텍스트 처리"""
        template = self._get_gomin_template(text_gomin)
        messages = [
            {"role": "system", "content": self.system_content},
            {"role": "assistant", "content": self.introduction},
            {"role": "user", "content": template}
        ]
        
        response, exec_time = self._call_gpt(messages)
        return self._parse_response(response), exec_time

    @staticmethod
    def _get_gomin_template(text: str) -> str:
        """고민 처리를 위한 템플릿 생성"""
        return f"""
        당신은 상대방의 고민을 상담하고 있습니다.
        논어의 핵심 내용을 바탕으로 상대방의 고민에 도움을 줄 수 있는 한자를 반환해야 합니다.

        STEP별로 작업을 수행하면서 그 결과를 아래의 <출력 결과> JSON 포맷에 작성하세요.
        STEP-1. 아래 세 개의 백틱으로 구분된 텍스트를 원문 그대로 읽어올 것
        STEP-2. 입력받은 텍스트가 고민이 아니라면 false를 표기하고 STEP-3를 진행하지 말 것. ex) 안녕하세요 -> false
        STEP-3. 텍스트에 어떤 <고민>이 들어있는지 요약할 것
        STEP-4. <고민>에서 나타나는 상대방의 <부족함>을 이야기하고, 그와 관련된 仁의 <하위개념>이 무엇인지 고르고, <선택한 이유>와 함께 반환할 것
        ```{text}```
        ---
        <출력 결과> : {{"STEP-1": <입력텍스트>, "STEP-2": <True/False>, "STEP-3": {{"요약": <고민>}}, "STEP-4": {{"부족함": <부족함>, "하위개념": <하위개념>, "이유": <선택한 이유>}}}}
        """
    
    def generate_advice(self, gomin_response: Dict) -> Tuple[Dict, float]:
        """조언 생성"""
        noneo = self._load_random_noneo()
        template = self._get_advice_template(noneo)
        
        messages = [
            {"role": "system", "content": self.system_content},
            {"role": "assistant", "content": self.introduction},
            {"role": "user", "content": gomin_response["STEP-1"]},
            {"role": "assistant", "content": self._create_context_message(gomin_response)},
            {"role": "user", "content": template}
        ]
        
        response, exec_time = self._call_gpt(messages)
        return self._parse_response(response), exec_time
    
    @staticmethod
    def _load_random_noneo(count: int = 20) -> list:
        """무작위 논어 구절 로드 - 원문 제외"""
        with open(Path('./files/noneo_data.json'), 'r', encoding='utf-8') as file:
            data = json.load(file)
            # 각 항목에서 원문을 제외한 정보만 추출
            simplified_data = [
                {
                    "편": item["편"],
                    "구절번호": item["구절번호"],
                    "내용": item["내용"]
                }
                for item in data['data']
            ]
            return random.sample(simplified_data, count)
    
    @staticmethod
    def _get_advice_template(noneo: list) -> str:
        """조언 생성을 위한 템플릿 생성 - 원문 제외된 데이터 사용"""
        return f"""
        당신은 이제 고민에 대한 해결책을 제시해야 합니다.

        STEP별로 작업을 수행하면서 그 결과를 아래의 <출력 결과> JSON 포맷에 작성하세요.
        STEP-1. 앞선 대화에서 말한 <고민>과 <부족함>, <하위개념>과 그를 <선택한 이유>를 다시 자세하게 서술할 것
        STEP-2. <부족함>을 보완할 수 있는 논어의 구절 중 하나만 다음 중에서 찾아서 반환할 것:
        {[f"{item['편']}-{item['구절번호']}: {item['내용']}" for item in noneo]}
        STEP-3. STEP-1에서 정리한 것을 토대로 <구절을 선택한 이유>를 적을 것
        STEP-4. STEP-1에서 정리한 내용과 <구절을 선택한 이유>를 이용해 상대방을 진심으로 도울 수 있는 <조언>을 작성할 것. <조언>은 하위 개념과 함께 설명하며 길게 작성할 것
        ---
        <출력 결과> : {{"STEP-1": {{"고민": <고민>, "부족": <부족함>, "하위개념": <하위개념>, "이유": <선택한 이유>}}, "STEP-2": <논어구절>, "STEP-3": <구절을 선택한 이유>, "STEP-4": <조언>}}
        """
    
    @staticmethod
    def _create_context_message(gomin_response: Dict) -> str:
        """컨텍스트 메시지 생성"""
        return f"""자네의 고민은 {gomin_response["STEP-3"]["요약"]}이네.
                  그 상황에서 자네의 부족함은 {gomin_response["STEP-4"]["부족함"]}일 것이고, 
                  그것을 보완할 수 있는 인의 하위개념은 {gomin_response["STEP-4"]["하위개념"]}에 해당하네. 
                  그것을 고른 이유는 {gomin_response["STEP-4"]["이유"]}와 같네."""