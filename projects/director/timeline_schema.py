from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Literal, Optional, List, Dict, Any
import json
from pathlib import Path


MediaType = Literal["image", "video"]
SceneType = Literal["hook", "answer", "story", "fact", "ending"]


@dataclass
class Media:
    type: MediaType
    src: str
    fit: str = "cover"


@dataclass
class Scene:
    id: str
    type: SceneType
    start: float
    duration: float
    title: str
    narration: str
    subtitle: str
    media: Media
    keywords: List[str]


@dataclass
class Timeline:
    version: str
    episode_id: str
    title: str
    fps: int
    width: int
    height: int
    duration: float
    bgm: Optional[str]
    voice: Optional[str]
    scenes: List[Scene]


def save_timeline(timeline: Timeline, output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data: Dict[str, Any] = asdict(timeline)

    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)