# config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """애플리케이션 설정"""
    OPENAI_API_KEY: Optional[str] = None
    NONEO_DATA_PATH: str = './files/noneo_data.json'