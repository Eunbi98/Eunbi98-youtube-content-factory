from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
RUNNER_DIR = ROOT_DIR / "projects" / "runner"
MEDIA_DIR = ROOT_DIR / "projects" / "media"

for module_path in (RUNNER_DIR, MEDIA_DIR):
    module_text = str(module_path)
    if module_text not in sys.path:
        sys.path.insert(0, module_text)

from pipeline_context import FactoryPaths, FactoryRunOptions  # noqa: E402
from recover_scene_media import (  # noqa: E402
    SceneMediaRecoveryError,
    recover_missing_scene_media,
)
from runner_factory_core import FactoryCore, FactoryExecutionError  # noqa: E402


def normalize_episode_id(raw_episode: str) -> str:
    episode = raw_episode.strip().lower()
    number_text = episode[2:] if episode.startswith("ep") else episode
    if not number_text.isdigit():
        raise ValueError(
            "에피소드 형식이 올바르지 않습니다. 예: ep008 또는 008"
        )
    return f"ep{int(number_text):03d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Director, Timeline, Assets, Remotion 통합 Factory Runner"
    )
    parser.add_argument("--episode", required=True, help="예: ep008")
    parser.add_argument(
        "--rebuild-timeline",
        action="store_true",
        help="기존 timeline.json이 있어도 다시 생성합니다.",
    )
    parser.add_argument(
        "--skip-typecheck",
        action="store_true",
        help="TypeScript 검사를 생략합니다.",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Timeline과 Assets 검증까지만 실행합니다.",
    )
    parser.add_argument(
        "--no-media-fallback",
        action="store_true",
        help="누락 Scene의 인접 이미지 재사용 복구를 끕니다.",
    )
    return parser.parse_args()


def _run_factory(
    *,
    paths: FactoryPaths,
    rebuild_timeline: bool,
    skip_typecheck: bool,
    validate_only: bool,
) -> bool:
    options = FactoryRunOptions(
        rebuild_timeline=rebuild_timeline,
        skip_typecheck=skip_typecheck,
        validate_only=validate_only,
    )
    result = FactoryCore(paths=paths, options=options).run()
    return result.succeeded


def main() -> int:
    args = parse_args()
    try:
        episode_id = normalize_episode_id(args.episode)
    except ValueError as exc:
        print(f"[실패] {exc}")
        return 2

    paths = FactoryPaths.create(root_dir=ROOT_DIR, episode_id=episode_id)

    try:
        succeeded = _run_factory(
            paths=paths,
            rebuild_timeline=args.rebuild_timeline,
            skip_typecheck=args.skip_typecheck,
            validate_only=args.validate_only,
        )
        return 0 if succeeded else 1
    except FactoryExecutionError:
        if args.no_media_fallback or args.validate_only:
            return 1

    print("\n[자동 복구] 누락 Scene에 인접 장면 미디어를 재사용합니다.")
    try:
        recovered = recover_missing_scene_media(
            timeline_path=paths.source_timeline,
            assets_dir=paths.source_assets_dir,
        )
    except (OSError, SceneMediaRecoveryError) as exc:
        print(f"[자동 복구 실패] {exc}")
        return 1

    if not recovered:
        print("[자동 복구 실패] 복구할 누락 Scene을 찾지 못했습니다.")
        return 1

    print("[자동 복구 완료] " + ", ".join(recovered))
    print("[자동 재실행] 복구된 Timeline으로 렌더를 다시 시작합니다.")

    try:
        succeeded = _run_factory(
            paths=paths,
            rebuild_timeline=False,
            skip_typecheck=args.skip_typecheck,
            validate_only=False,
        )
    except FactoryExecutionError:
        return 1

    return 0 if succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
