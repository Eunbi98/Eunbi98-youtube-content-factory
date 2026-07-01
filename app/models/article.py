from dataclasses import dataclass, field
from typing import List


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: str

    # 본문
    content: str = ""

    # 전처리된 본문
    cleaned_content: str = ""

    # 랭킹 점수
    score: int = 0

    # AI 결과물
    summary: str = ""
    script: str = ""
    thumbnail: str = ""

    hashtags: List[str] = field(default_factory=list)

    # 처리 상태
    status: str = "COLLECTED"