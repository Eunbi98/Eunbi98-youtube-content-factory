from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.media.media_types import MediaPlanItem, MediaType, PreferredSource


REAL_FIRST_TYPES = {"real_video", "real_image", "official_image"}


class MediaSelector:
    def generate_from_files(
        self,
        script_path: Path | str,
        visual_plan_path: Path | str,
        knowledge_pack_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> list[dict[str, object]]:
        script_file = Path(script_path)
        visual_plan_file = Path(visual_plan_path)
        knowledge_pack_file = Path(knowledge_pack_path)
        target_dir = Path(output_dir) if output_dir else script_file.parent

        script = self._load_json_object(script_file)
        visual_plan = self._load_json_list(visual_plan_file)
        knowledge_pack = self._load_json_object(knowledge_pack_file)
        media_plan = self.generate(script, visual_plan, knowledge_pack)

        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "media_plan.json"
        markdown_path = target_dir / "media_plan.md"

        json_path.write_text(
            json.dumps(media_plan, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(
            self._render_markdown(media_plan),
            encoding="utf-8",
        )

        return media_plan

    def generate(
        self,
        script: dict[str, Any],
        visual_plan: list[dict[str, Any]],
        knowledge_pack: dict[str, Any],
    ) -> list[dict[str, object]]:
        narration_lines = script.get("narration_lines", [])
        if not isinstance(narration_lines, list):
            raise ValueError("script.json must contain narration_lines array.")

        if len(visual_plan) != len(narration_lines):
            raise ValueError("visual_plan scene count must match narration_lines.")

        sources_text = self._sources_text(knowledge_pack)
        items = [
            self._select_item(
                scene=index,
                narration=str(narration),
                visual_item=visual_plan[index - 1],
                sources_text=sources_text,
            )
            for index, narration in enumerate(narration_lines, start=1)
        ]
        self._ensure_real_first_ratio(items)
        return [item.to_dict() for item in items]

    def _select_item(
        self,
        scene: int,
        narration: str,
        visual_item: dict[str, Any],
        sources_text: str,
    ) -> MediaPlanItem:
        compact = self._compact(narration)
        visual_type = str(visual_item.get("visual_type", ""))
        visual_keywords = " ".join(str(item) for item in visual_item.get("search_keywords", []))
        combined = f"{compact} {visual_keywords}"

        if self._is_mars_ending(compact):
            return self._official_image(
                scene,
                narration,
                preferred_source="NASA" if "NASA" in sources_text else "ESA",
                reason="화성 엔딩은 NASA/ESA 공식 화성 이미지가 존재할 가능성이 높아 AI 이미지보다 공식 이미지를 우선한다.",
                queries=[
                    "NASA Mars official image",
                    "NASA Mars surface image public domain",
                    "ESA Mars Express official image",
                ],
                visual_note="화성 표면 또는 지구-화성 대비 이미지를 사용하고 질문형 엔딩 분위기만 살린다.",
            )

        if self._mentions_astronaut_or_routine(combined):
            return self._real_video(
                scene,
                narration,
                preferred_source="NASA",
                reason="ISS, 우주비행사, 운동, 귀환 장면은 실제 NASA/ESA 영상 자료가 있을 가능성이 높다.",
                queries=[
                    "NASA astronaut exercise ISS video",
                    "NASA astronaut return to Earth rehabilitation video",
                    "ESA astronaut exercise International Space Station video",
                ],
                visual_note="실제 ISS 운동 장면, 귀환 직후 보행 보조, 재활 장면을 우선 탐색한다.",
            )

        if self._mentions_record_or_nasa(combined):
            return self._official_image(
                scene,
                narration,
                preferred_source="NASA",
                reason="Scott Kelly, Frank Rubio, NASA 기록 관련 장면은 NASA 공식 이미지나 영상이 가장 신뢰도 높다.",
                queries=[
                    "NASA Scott Kelly official image",
                    "NASA Frank Rubio official image",
                    "NASA astronaut record holders ISS image",
                ],
                visual_note="공식 우주비행사 사진 또는 ISS 이미지를 사용하고 숫자는 후반 편집에서 오버레이한다.",
            )

        if self._is_body_change_explainer(compact):
            media_type = "infographic" if self._is_number_scene(compact) else "animation"
            return MediaPlanItem(
                scene=scene,
                narration=narration,
                media_type=media_type,
                preferred_source="Generated",
                source_confidence=2,
                reason="체액 이동, 시야 변화, 골밀도 변화는 실제 촬영보다 도식화가 이해를 돕는다.",
                search_queries=[
                    "microgravity fluid shift animation",
                    "spaceflight vision change animation",
                    "bone density loss microgravity infographic",
                ],
                fallback_media_type="ai_image",
                visual_note="NASA verified facts를 바탕으로 단순한 화살표, 눈 아이콘, 골밀도 그래프를 만든다.",
            )

        if self._is_number_scene(compact) or visual_type == "infographic":
            return MediaPlanItem(
                scene=scene,
                narration=narration,
                media_type="infographic",
                preferred_source="Generated",
                source_confidence=2,
                reason="숫자가 핵심인 장면이라 수치 중심 인포그래픽이 가장 명확하다.",
                search_queries=[
                    "space duration infographic 382 days",
                    "astronaut long duration mission infographic",
                ],
                fallback_media_type="ai_image",
                visual_note="숫자를 크게 두고 배경에는 공식 ISS 이미지를 보조로 사용할 수 있다.",
            )

        if visual_type == "real_image":
            return self._official_image(
                scene,
                narration,
                preferred_source="NASA",
                reason="Visual Director가 실제 이미지 계열을 제안했고 공식 우주 자료가 적합하다.",
                queries=[
                    "NASA official space station image",
                    "NASA human spaceflight official image",
                ],
                visual_note="공식 이미지 위에 짧은 자막을 얹어 신뢰감을 유지한다.",
            )

        if self._is_emotional(compact):
            return MediaPlanItem(
                scene=scene,
                narration=narration,
                media_type="ai_image",
                preferred_source="Generated",
                source_confidence=2,
                reason="짧은 감정 전환 문장이라 실제 자료보다 상징적 이미지가 리듬을 만든다.",
                search_queries=[
                    "cinematic astronaut emotional space image reference",
                    "human body earth gravity symbolic image",
                ],
                fallback_media_type="ai_image",
                visual_note="과장된 공포 이미지 대신 차분한 우주 실루엣으로 감정 전환만 만든다.",
            )

        return MediaPlanItem(
            scene=scene,
            narration=narration,
            media_type="animation",
            preferred_source="Generated",
            source_confidence=2,
            reason="설명 보조용 전환 장면으로 간단한 애니메이션이 적합하다.",
            search_queries=["space medicine explainer animation reference"],
            fallback_media_type="ai_image",
            visual_note="검은 우주 배경 위에 간단한 라인 애니메이션을 사용한다.",
        )

    def _real_video(
        self,
        scene: int,
        narration: str,
        preferred_source: PreferredSource,
        reason: str,
        queries: list[str],
        visual_note: str,
    ) -> MediaPlanItem:
        return MediaPlanItem(
            scene=scene,
            narration=narration,
            media_type="real_video",
            preferred_source=preferred_source,
            source_confidence=self._confidence(preferred_source),
            reason=reason,
            search_queries=queries,
            fallback_media_type="ai_image",
            visual_note=visual_note,
        )

    def _official_image(
        self,
        scene: int,
        narration: str,
        preferred_source: PreferredSource,
        reason: str,
        queries: list[str],
        visual_note: str,
    ) -> MediaPlanItem:
        return MediaPlanItem(
            scene=scene,
            narration=narration,
            media_type="official_image",
            preferred_source=preferred_source,
            source_confidence=self._confidence(preferred_source),
            reason=reason,
            search_queries=queries,
            fallback_media_type="ai_image",
            visual_note=visual_note,
        )

    def _ensure_real_first_ratio(self, items: list[MediaPlanItem]) -> None:
        real_first_count = sum(item.media_type in REAL_FIRST_TYPES for item in items)
        ratio = real_first_count / len(items) if items else 0
        if ratio < 0.5:
            raise ValueError(f"Real/public media priority ratio is too low: {ratio:.2f}")

    def _confidence(self, preferred_source: PreferredSource) -> int:
        if preferred_source in ("NASA", "ESA"):
            return 5
        if preferred_source in ("Wikipedia", "Stock"):
            return 3
        return 2

    def _is_mars_ending(self, text: str) -> bool:
        return "화성" in text

    def _mentions_astronaut_or_routine(self, text: str) -> bool:
        return any(
            keyword.lower() in text.lower()
            for keyword in (
                "ISS",
                "우주비행사",
                "운동",
                "귀환",
                "돌아오면",
                "걷는",
                "재활",
                "return to Earth",
                "astronaut exercise",
                "Frank Rubio ISS return video",
            )
        )

    def _mentions_record_or_nasa(self, text: str) -> bool:
        return any(
            keyword.lower() in text.lower()
            for keyword in (
                "NASA",
                "Scott Kelly",
                "Frank Rubio",
                "371일",
                "340일",
                "382일",
                "record holders",
            )
        )

    def _is_body_change_explainer(self, text: str) -> bool:
        return any(
            keyword in text
            for keyword in (
                "체액",
                "시야",
                "눈",
                "골밀도",
                "뼈",
                "근육",
                "중력",
            )
        )

    def _is_number_scene(self, text: str) -> bool:
        return any(char.isdigit() for char in text)

    def _is_emotional(self, text: str) -> bool:
        return any(
            keyword in text
            for keyword in ("아닙니다", "그렇다면", "인간의 몸")
        )

    def _compact(self, text: str) -> str:
        return " ".join(str(text).split())

    def _sources_text(self, knowledge_pack: dict[str, Any]) -> str:
        return json.dumps(
            knowledge_pack.get("sources", []),
            ensure_ascii=False,
        )

    def _load_json_object(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object.")
        return data

    def _load_json_list(self, path: Path) -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError(f"{path} must contain a JSON array.")
        return data

    def _render_markdown(self, media_plan: list[dict[str, object]]) -> str:
        lines = [
            "# Episode 001 Media Plan",
            "",
            "| Scene | Media | Source | Confidence | Narration | Note |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for item in media_plan:
            narration = str(item["narration"]).replace("\n", "<br>")
            lines.append(
                "| "
                f"{item['scene']} | "
                f"{item['media_type']} | "
                f"{item['preferred_source']} | "
                f"{item['source_confidence']} | "
                f"{narration} | "
                f"{item['visual_note']} |"
            )

        real_first_count = sum(
            item["media_type"] in REAL_FIRST_TYPES
            for item in media_plan
        )
        ai_count = sum(item["media_type"] == "ai_image" for item in media_plan)
        total = len(media_plan) or 1
        lines.extend([
            "",
            "## Ratios",
            "",
            f"- Real/public-first media: {real_first_count}/{len(media_plan)} ({real_first_count / total:.1%})",
            f"- AI image primary use: {ai_count}/{len(media_plan)} ({ai_count / total:.1%})",
            "",
        ])
        return "\n".join(lines)
