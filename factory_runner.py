from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
RUNNER_DIR = ROOT_DIR / "projects" / "runner"

if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from pipeline_context import (  # noqa: E402
    FactoryPaths,
    FactoryRunOptions,
)
from runner_factory_core import (  # noqa: E402
    FactoryCore,
    FactoryExecutionError,
)


def normalize_episode_id(
    raw_episode: str,
) -> str:
    episode = raw_episode.strip().lower()

    if episode.startswith("ep"):
        number_text = episode[2:]
    else:
        number_text = episode

    if not number_text.isdigit():
        raise ValueError(
            "에피소드 형식이 올바르지 않습니다. "
            "예: ep008 또는 008"
        )

    return f"ep{int(number_text):03d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Director, Timeline, Assets, Remotion을 "
            "통합 실행하는 Factory Runner입니다."
        )
    )

    parser.add_argument(
        "--episode",
        required=True,
        help="처리할 에피소드 ID. 예: ep008",
    )

    parser.add_argument(
        "--rebuild-timeline",
        action="store_true",
        help=(
            "기존 timeline.json이 있어도 "
            "Director로 다시 생성합니다."
        ),
    )

    parser.add_argument(
        "--skip-typecheck",
        action="store_true",
        help="TypeScript 검사를 생략합니다.",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help=(
            "Timeline과 Assets 검증까지만 실행하고 "
            "렌더는 생략합니다."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        episode_id = normalize_episode_id(
            args.episode
        )
    except ValueError as exc:
        print(f"[실패] {exc}")
        return 2

    paths = FactoryPaths.create(
        root_dir=ROOT_DIR,
        episode_id=episode_id,
    )

    options = FactoryRunOptions(
        rebuild_timeline=(
            args.rebuild_timeline
        ),
        skip_typecheck=(
            args.skip_typecheck
        ),
        validate_only=(
            args.validate_only
        ),
    )

    try:
        result = FactoryCore(
            paths=paths,
            options=options,
        ).run()
    except FactoryExecutionError:
        return 1

    return 0 if result.succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
