from __future__ import annotations

import importlib
import sys
from pathlib import Path


class DirectorExecutionError(RuntimeError):
    """Director 실행 실패."""


def _load_director(
    director_dir: Path,
):
    director_dir_text = str(
        director_dir.resolve()
    )

    if director_dir_text in sys.path:
        sys.path.remove(
            director_dir_text
        )

    sys.path.insert(
        0,
        director_dir_text,
    )

    cached_director = sys.modules.get(
        "director"
    )

    if cached_director is not None:
        cached_path = Path(
            getattr(
                cached_director,
                "__file__",
                "",
            )
        ).resolve()

        expected_path = (
            director_dir
            / "director.py"
        ).resolve()

        if cached_path != expected_path:
            del sys.modules["director"]

    try:
        director_module = importlib.import_module(
            "director"
        )
    except ImportError as exc:
        raise DirectorExecutionError(
            f"Director import 실패: {exc}"
        ) from exc

    try:
        director_class = getattr(
            director_module,
            "Director",
        )
        director_error = getattr(
            director_module,
            "DirectorError",
        )
    except AttributeError as exc:
        raise DirectorExecutionError(
            "Director 모듈 구조가 올바르지 않습니다."
        ) from exc

    return director_class, director_error


def build_episode_timeline(
    *,
    root_dir: Path,
    episode_id: str,
) -> Path:
    director_dir = (
        root_dir
        / "projects"
        / "director"
    )

    output_path = (
        root_dir
        / "projects"
        / "episodes"
        / episode_id
        / "timeline.json"
    )

    if not director_dir.exists():
        raise DirectorExecutionError(
            f"Director 폴더가 없습니다: {director_dir}"
        )

    director_class, director_error = (
        _load_director(
            director_dir
        )
    )

    try:
        result = director_class().build(
            episode_id=episode_id,
            output_path=output_path,
        )
    except director_error as exc:
        raise DirectorExecutionError(
            str(exc)
        ) from exc
    except Exception as exc:
        raise DirectorExecutionError(
            f"Director 처리 중 오류: {exc}"
        ) from exc

    if not output_path.exists():
        raise DirectorExecutionError(
            "Director 실행은 완료됐지만 "
            "timeline.json이 생성되지 않았습니다: "
            f"{output_path}"
        )

    if result.scene_count <= 0:
        raise DirectorExecutionError(
            "Director가 장면이 없는 Timeline을 생성했습니다."
        )

    if result.total_duration <= 0:
        raise DirectorExecutionError(
            "Director가 길이가 0인 Timeline을 생성했습니다."
        )

    return output_path
