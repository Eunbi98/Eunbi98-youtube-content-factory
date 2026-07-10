from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.visual_director.visual_plan_types import CameraMotion, VisualPlanItem, VisualType


NUMBER_PATTERN = re.compile(r"\d+(?:[~.-]\d+(?:\.\d+)?)?%?(?:일|시간|년|개월)?")


class VisualDirector:
    DEFAULT_DURATION = 4.2

    def generate_from_file(
        self,
        script_path: Path | str,
        output_path: Path | str | None = None,
    ) -> list[dict[str, object]]:
        script_file = Path(script_path)
        script_data = self._load_script(script_file)
        visual_plan = self.generate(script_data)

        target_path = (
            Path(output_path)
            if output_path
            else script_file.with_name("visual_plan.json")
        )
        target_path.write_text(
            json.dumps(visual_plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return visual_plan

    def generate(self, script_data: dict[str, Any]) -> list[dict[str, object]]:
        narration_lines = script_data.get("narration_lines", [])
        if not isinstance(narration_lines, list):
            raise ValueError("script.json must contain narration_lines array.")

        plan = [
            self._build_scene(index=index, narration=str(narration))
            for index, narration in enumerate(narration_lines, start=1)
        ]
        return [
            item.to_dict()
            for item in plan
        ]

    def _load_script(self, script_file: Path) -> dict[str, Any]:
        data = json.loads(script_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("script.json must contain a JSON object.")
        return data

    def _build_scene(self, index: int, narration: str) -> VisualPlanItem:
        compact = self._compact(narration)
        visual_type, reason = self._select_visual_type(compact)

        return VisualPlanItem(
            scene=index,
            narration=narration,
            visual_type=visual_type,
            reason=reason,
            search_keywords=self._build_search_keywords(compact, visual_type),
            image_prompt=self._build_image_prompt(compact, visual_type),
            camera_motion=self._select_camera_motion(index, visual_type),
            duration=self.DEFAULT_DURATION,
        )

    def _select_visual_type(self, narration: str) -> tuple[VisualType, str]:
        if self._has_number(narration):
            return (
                "infographic",
                "숫자 표현이 핵심 정보라 수치가 한눈에 보이는 인포그래픽이 가장 적합하다.",
            )

        if self._mentions_astronaut(narration):
            return (
                "real_video",
                "우주비행사 행동은 실제 ISS 영상 자료가 있으면 가장 신뢰감 있게 보인다.",
            )

        if self._mentions_nasa(narration):
            return (
                "real_image",
                "NASA 관련 소재는 공식 이미지 자료를 우선 사용하는 것이 적합하다.",
            )

        if self._is_explanation(narration):
            return (
                "animation",
                "눈에 보이지 않는 신체 변화 설명은 애니메이션 도식이 이해를 돕는다.",
            )

        if self._is_emotional(narration):
            return (
                "ai_image",
                "감정적 질문이나 추상적 결론은 상징적인 AI 이미지가 분위기를 만들기 좋다.",
            )

        return (
            "animation",
            "짧은 전환 문장은 리듬을 유지하는 간단한 애니메이션이 적합하다.",
        )

    def _build_search_keywords(self, narration: str, visual_type: VisualType) -> list[str]:
        if visual_type == "real_video":
            return [
                "NASA astronaut exercise ISS video",
                "International Space Station astronaut workout",
                "Frank Rubio ISS return video",
            ]

        if visual_type == "real_image":
            return [
                "NASA official astronaut space image",
                "NASA International Space Station crew photo",
            ]

        if visual_type == "infographic":
            keywords = ["spaceflight human body infographic"]
            if "382일" in narration:
                keywords.append("382 days in space timeline infographic")
            if "1~1.5%" in narration:
                keywords.append("bone density loss microgravity 1.5 percent infographic")
            if "2시간" in narration:
                keywords.append("astronaut daily exercise two hours infographic")
            return keywords

        if visual_type == "animation":
            if "체액" in narration or "머리" in narration:
                return [
                    "microgravity fluid shift animation",
                    "spaceflight body fluid shift head animation",
                ]
            if "눈" in narration or "보이기" in narration:
                return [
                    "spaceflight vision change animation",
                    "astronaut eye pressure microgravity animation",
                ]
            if "지구" in narration or "걷는" in narration:
                return [
                    "astronaut return to Earth rehabilitation animation",
                    "gravity readaptation animation",
                ]
            return ["space medicine explainer animation"]

        return [
            "cinematic astronaut looking at Mars",
            "human body designed for Earth symbolic image",
        ]

    def _build_image_prompt(self, narration: str, visual_type: VisualType) -> str:
        if visual_type in ("real_video", "real_image"):
            return ""

        if visual_type == "infographic":
            return (
                "Clean vertical shorts infographic, high contrast Korean captions, "
                f"visualize this idea: {narration}"
            )

        if visual_type == "animation":
            return (
                "Simple medical explainer animation frame, dark space background, "
                f"clear arrows and labels for: {narration}"
            )

        return (
            "Cinematic AI image, lonely astronaut silhouette, Earth and Mars mood, "
            f"emotional visual metaphor for: {narration}"
        )

    def _select_camera_motion(
        self,
        scene: int,
        visual_type: VisualType,
    ) -> CameraMotion:
        if visual_type == "infographic":
            return "none"

        if visual_type == "real_video":
            return "pan_right"

        if visual_type == "real_image":
            return "zoom_in"

        if visual_type == "animation":
            return "pan_left" if scene % 2 == 0 else "zoom_in"

        return "zoom_out"

    def _has_number(self, narration: str) -> bool:
        return bool(NUMBER_PATTERN.search(narration))

    def _mentions_astronaut(self, narration: str) -> bool:
        return any(
            keyword in narration
            for keyword in ("우주비행사", "운동", "걷는", "돌아오면", "적응")
        )

    def _mentions_nasa(self, narration: str) -> bool:
        return any(
            keyword in narration
            for keyword in ("NASA", "나사", "Scott Kelly", "Frank Rubio")
        )

    def _is_explanation(self, narration: str) -> bool:
        return any(
            keyword in narration
            for keyword in (
                "중력",
                "체액",
                "머리",
                "눈",
                "보이기",
                "몸",
                "뼈",
                "근육",
            )
        )

    def _is_emotional(self, narration: str) -> bool:
        return any(
            keyword in narration
            for keyword in ("아닙니다", "그렇다면", "화성", "인간의 몸")
        )

    def _compact(self, narration: str) -> str:
        return " ".join(str(narration).split())
