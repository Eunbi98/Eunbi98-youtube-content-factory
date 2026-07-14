from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent
PROJECT_ROOT = CURRENT_FILE.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if str(QUIZ_DIR) not in sys.path:
    sys.path.insert(0, str(QUIZ_DIR))

from quiz_content_builder import (  # noqa: E402
    QuizContentBuildError,
    QuizContentBuilder,
)
from projects.plugins.quiz.quiz_scene_builder import (  # noqa: E402
    QuizSceneBuildError,
    QuizSceneBuilder,
)
from projects.plugins.quiz.quiz_story_builder import (  # noqa: E402
    QuizStoryBuilder,
    QuizValidationError,
)
from projects.plugins.quiz.quiz_timeline_builder import (  # noqa: E402
    QuizTimelineBuildError,
    QuizTimelineBuilder,
)


def _parse_categories(value: str) -> set[str] | None:
    categories = {
        item.strip().lower()
        for item in value.split(",")
        if item.strip()
    }
    return categories or None


def _default_pools(level: str) -> tuple[Path, ...]:
    output_dir = QUIZ_DIR / "output"
    candidates = (
        output_dir / f"question_pool_{level}_classified.json",
        output_dir / f"question_pool_{level}_validated.json",
        output_dir / f"question_pool_{level}.json",
    )
    existing = tuple(path for path in candidates if path.exists())
    return existing or (candidates[-1],)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Question Pool에서 quiz input, story, scenes, timeline을 한 번에 생성합니다."
        )
    )
    parser.add_argument("--episode-id", required=True)
    parser.add_argument(
        "--level",
        required=True,
        choices=("elementary", "middle", "high", "current"),
    )
    parser.add_argument("--title", default="오늘의 상식 퀴즈")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--seed", type=int, default=11)
    parser.add_argument("--minimum-quality", type=float, default=70.0)
    parser.add_argument("--categories", default="")
    parser.add_argument("--question-pool", type=Path, default=None)
    parser.add_argument("--ending-text", default="몇 문제를 맞혔나요?")
    parser.add_argument(
        "--ending-tts",
        default="몇 문제를 맞혔는지 댓글로 남겨주세요.",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()
    question_pools = (
        (args.question_pool,)
        if args.question_pool is not None
        else _default_pools(args.level)
    )
    episode_id = QuizContentBuilder._normalize_episode_id(args.episode_id)
    episode_dir = PROJECT_ROOT / "projects" / "episodes" / episode_id
    quiz_input = QUIZ_DIR / "input" / f"{episode_id}_quiz.json"
    quiz_story = episode_dir / "quiz_story.json"
    quiz_scenes = episode_dir / "quiz_scenes.json"
    timeline = episode_dir / "timeline.json"

    try:
        payload = QuizContentBuilder().build(
            question_pool_paths=question_pools,
            output_path=quiz_input,
            episode_id=episode_id,
            title=args.title,
            count=args.count,
            level=args.level,
            seed=args.seed,
            minimum_quality=args.minimum_quality,
            categories=_parse_categories(args.categories),
            ending_text=args.ending_text,
            ending_tts=args.ending_tts,
        )

        story = QuizStoryBuilder().build(
            source_path=quiz_input,
            output_path=quiz_story,
        )
        scenes = QuizSceneBuilder().build_from_file(
            story_path=quiz_story,
            output_path=quiz_scenes,
        )
        built_timeline = QuizTimelineBuilder().build_from_file(
            scenes_path=quiz_scenes,
            output_path=timeline,
        )

        print("=" * 60)
        print(" Release 8.4.5 Quiz Builder 완료")
        print("=" * 60)
        print(f"       에피소드: {episode_id}")
        print(f"       난이도: {args.level}")
        print(f"       문제: {payload['question_count']}개")
        print(f"       장면: {scenes.scene_count}개")
        print(f"       길이: {float(built_timeline['totalDuration']):.1f}초")
        print(f"       입력: {quiz_input.resolve()}")
        print(f"       Story: {quiz_story.resolve()}")
        print(f"       Scenes: {quiz_scenes.resolve()}")
        print(f"       Timeline: {timeline.resolve()}")
        return 0

    except (
        FileNotFoundError,
        OSError,
        QuizContentBuildError,
        QuizValidationError,
        QuizSceneBuildError,
        QuizTimelineBuildError,
    ) as exc:
        print("=" * 60)
        print(" Release 8.4.5 Quiz Builder 실패")
        print("=" * 60)
        print(f"       오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
