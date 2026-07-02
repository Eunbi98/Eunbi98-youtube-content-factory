from dataclasses import dataclass, field
from typing import List


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: str

    content: str = ""
    cleaned_content: str = ""

    score: int = 0

    summary: str = ""
    script: str = ""
    thumbnail: str = ""

    hashtags: List[str] = field(default_factory=list)
    scenes: List[dict] = field(default_factory=list)

    status: str = "COLLECTED"