from __future__ import annotations

import argparse
import json
import os
import shutil
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


LANGUAGE_SETTINGS = {
    "ko": {
        "language": "ko-KR",
        "voice": "ko-KR-SunHiNeural",
    },
    "en": {
        "language": "en-US",
        "voice": "en-US-JennyNeural",
    },
}

ENGLISH_EPISODE_OFFSET = 1000


def normalize_episode_id(raw_episode: str) -> str:
    episode = raw_episode.strip().lower()
    number_text = episode[2:] if episode.startswith("ep") else episode
    if not number_text.isdigit():
        raise ValueError(
            "에피소드 형식이 올바르지 않습니다. 예: ep008 또는 008"
        )
    return f"ep{int(number_text):03d}"


def english_episode_id(base_episode_id: str) -> str:
    number = int(base_episode_id[2:])
    return f"ep{number + ENGLISH_EPISODE_OFFSET:03d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Director, Timeline, Assets, Remotion 통합 Factory Runner"
    )
    parser.add_argument("--episode", required=True, help="예: ep008")
    parser.add_argument(
        "--lang",
        choices=tuple(LANGUAGE_SETTINGS),
        default="ko",
        help="제작 언어. 기본값 ko, 영어판은 en",
    )
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


def purge_stale_generated_files(episode_id: str) -> None:
    episode_dir = ROOT_DIR / "projects" / "episodes" / episode_id

    directories = [
        episode_dir / "tts",
        episode_dir / "audio",
        ROOT_DIR / "projects" / "tts" / episode_id,
        ROOT_DIR / "projects" / "remotion" / "public" / episode_id,
    ]
    for directory in directories:
        if directory.exists():
            shutil.rmtree(directory, ignore_errors=True)
            print(f"[캐시 삭제] {directory}")

    files = [
        episode_dir / "timeline.json",
        episode_dir / "media_queries.json",
        ROOT_DIR / "projects" / "output" / f"{episode_id}.mp4",
    ]
    for file_path in files:
        if file_path.exists():
            file_path.unlink()
            print(f"[캐시 삭제] {file_path}")

    for pattern in ("*timing*.json", "*tts*.json", "*audio*.json"):
        for file_path in episode_dir.rglob(pattern):
            if file_path.is_file():
                file_path.unlink()
                print(f"[캐시 삭제] {file_path}")


def _prepare_english_variant(base_episode_id: str) -> str:
    source_dir = ROOT_DIR / "projects" / "episodes" / base_episode_id
    english_spec = source_dir / "episode.en.json"

    if not english_spec.exists():
        raise ValueError(
            "영어판 episode 파일이 없습니다.\n"
            f"필요 파일: {english_spec}\n"
            "먼저 해당 에피소드의 episode.en.json을 추가해 주세요."
        )

    variant_id = english_episode_id(base_episode_id)
    variant_dir = ROOT_DIR / "projects" / "episodes" / variant_id
    variant_dir.mkdir(parents=True, exist_ok=True)

    try:
        spec_data = json.loads(english_spec.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"영어판 episode 파일을 읽지 못했습니다: {exc}") from exc

    if not isinstance(spec_data, dict):
        raise ValueError("영어판 episode 파일의 최상위 값은 객체여야 합니다.")

    # 원본 파일에는 base EP 번호를 써도 되고 내부 영어 EP 번호를 써도 됩니다.
    # 실행 시에는 Remotion과 Director가 사용하는 숫자형 variant ID로 통일합니다.
    spec_data["episodeId"] = variant_id
    (variant_dir / "episode.json").write_text(
        json.dumps(spec_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    source_assets = source_dir / "assets"
    variant_assets = variant_dir / "assets"
    if source_assets.exists():
        shutil.copytree(
            source_assets,
            variant_assets,
            dirs_exist_ok=True,
        )
        print(
            f"[영어판] 한국어판 미디어 재사용: "
            f"{source_assets} -> {variant_assets}"
        )
    else:
        print(
            "[영어판] 한국어판 assets가 없어 "
            "영어판에서 미디어를 새로 수집합니다."
        )

    print(f"[영어판] 내부 에피소드 ID: {variant_id}")
    return variant_id


def _configure_language(lang: str) -> None:
    settings = LANGUAGE_SETTINGS[lang]
    os.environ["YCF_TTS_LANGUAGE"] = settings["language"]
    os.environ["YCF_TTS_VOICE"] = settings["voice"]
    print(
        f"[언어] {lang} / "
        f"{settings['language']} / {settings['voice']}"
    )


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
        base_episode_id = normalize_episode_id(args.episode)
        episode_id = (
            _prepare_english_variant(base_episode_id)
            if args.lang == "en"
            else base_episode_id
        )
        _configure_language(args.lang)
    except ValueError as exc:
        print(f"[실패] {exc}")
        return 2

    if args.rebuild_timeline:
        purge_stale_generated_files(episode_id)

    # rebuild가 작업 폴더의 생성 파일만 제거하므로 영어 스펙과
    # 한국어판 assets 재사용 상태를 다시 보장합니다.
    if args.lang == "en":
        try:
            episode_id = _prepare_english_variant(base_episode_id)
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
