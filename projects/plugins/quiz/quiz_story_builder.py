from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .quiz_schema import (
    QuizEpisode,
    QuizValidationError,
)


class QuizStoryBuilder:
    def load_source(
        self,
        source_path: Path,
    ) -> dict[str, Any]:
        source_path = source_path.resolve()

        if not source_path.exists():
            raise FileNotFoundError(
                f"퀴즈 입력 파일이 없습니다: "
                f"{source_path}"
            )

        if not source_path.is_file():
            raise QuizValidationError(
                f"퀴즈 입력 경로가 파일이 아닙니다: "
                f"{source_path}"
            )

        try:
            with source_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                loaded = json.load(file)
        except json.JSONDecodeError as error:
            raise QuizValidationError(
                "퀴즈 입력 JSON 형식이 올바르지 "
                f"않습니다: {error}"
            ) from error

        if not isinstance(loaded, dict):
            raise QuizValidationError(
                "퀴즈 입력 JSON 최상위 값은 "
                "객체여야 합니다."
            )

        return loaded

    def build(
        self,
        source_path: Path,
        output_path: Path,
    ) -> QuizEpisode:
        source_data = self.load_source(
            source_path
        )
        episode = QuizEpisode.from_dict(
            source_data
        )

        output_path = output_path.resolve()
        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temp_path = output_path.with_suffix(
            output_path.suffix + ".tmp"
        )

        with temp_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            json.dump(
                episode.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")

        temp_path.replace(output_path)

        return episode