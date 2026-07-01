from dataclasses import dataclass


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: str
    summary: str = ""
    content: str = ""