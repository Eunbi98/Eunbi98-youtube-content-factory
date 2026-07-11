from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from asset_manager import (
    AssetValidationError,
    collect_required_assets,
    sync_episode_assets,
)
from director_runner import (
    DirectorExecutionError,
    build_episode_timeline,
)
from pipeline_context import (
    FactoryPaths,
    FactoryRunContext,
    FactoryRunOptions,
    FactoryRunResult,
)
from pipeline_events import (
    ConsoleEventReporter,
    FactoryEvent,
    FactoryEventType,
)
from render_runner import (
    CommandExecutionError,
    render_episode,
    typecheck_remotion,
)
from timeline_validator import (
    TimelineValidationError,
    load_and_validate_timeline,
)


class FactoryExecutionError(RuntimeError):
    """Factory Pipeline 전체 실행 실패."""


class FactoryCore:
    def __init__(
        self,
        *,
        paths: FactoryPaths,
        options: FactoryRunOptions,
        reporter: ConsoleEventReporter | None = None,
    ) -> None:
        self._context = FactoryRunContext(
            paths=paths,
            options=options,
        )

        self._reporter = (
            reporter
            or ConsoleEventReporter()
        )

    def run(
        self,
    ) -> FactoryRunResult:
        started_at = time.perf_counter()

        self._emit(
            FactoryEventType.PIPELINE_STARTED,
            "시작",
            {
                "에피소드": (
                    self._context.paths.episode_id
                ),
                "Timeline": (
                    self._context.paths.source_timeline
                ),
                "Assets": (
                    self._context.paths.source_assets_dir
                ),
                "Audio": (
                    self._context.paths.source_audio_dir
                ),
            },
        )

        try:
            self._prepare_timeline()

            self._validate_timeline(
                stage_name="Timeline 초기 검증",
            )

            self._generate_tts_and_sync_duration()

            self._validate_timeline(
                stage_name=(
                    "TTS 동기화 Timeline 검증"
                ),
            )

            self._collect_and_sync_assets()

            self._validate_audio_files()

            if self._context.options.validate_only:
                self._context.status = "validated"
                self._context.elapsed_seconds = (
                    time.perf_counter()
                    - started_at
                )

                self._save_log()

                self._emit(
                    FactoryEventType.VALIDATION_COMPLETED,
                    "종료",
                    {
                        "결과": (
                            "Timeline, TTS, Assets "
                            "검증 완료"
                        ),
                        "로그": (
                            self._context.paths.log_path
                        ),
                        "소요": (
                            f"{self._context.elapsed_seconds:.2f}초"
                        ),
                    },
                )

                return self._build_result()

            self._publish_episode()
            self._run_typecheck()
            self._render()

            self._context.status = "success"
            self._context.elapsed_seconds = (
                time.perf_counter()
                - started_at
            )

            self._save_log()

            self._emit(
                FactoryEventType.PIPELINE_COMPLETED,
                "완료",
                {
                    "영상": (
                        self._context.paths.output_path
                    ),
                    "Public": (
                        self._context.paths.public_episode_dir
                    ),
                    "로그": (
                        self._context.paths.log_path
                    ),
                    "장면": (
                        f"{self._context.scene_count}개"
                    ),
                    "Assets": (
                        f"{self._context.copied_asset_count}개"
                    ),
                    "Audio": (
                        f"{self._context.copied_audio_count}개"
                    ),
                    "길이": (
                        f"{self._context.total_duration:.3f}초"
                    ),
                    "소요": (
                        f"{self._context.elapsed_seconds:.2f}초"
                    ),
                },
            )

            return self._build_result()

        except (
            TimelineValidationError,
            AssetValidationError,
            DirectorExecutionError,
            CommandExecutionError,
            OSError,
            RuntimeError,
            ValueError,
        ) as exc:
            self._context.status = "failed"
            self._context.error_message = str(exc)
            self._context.elapsed_seconds = (
                time.perf_counter()
                - started_at
            )

            self._save_log()

            self._emit(
                FactoryEventType.PIPELINE_FAILED,
                "실패",
                {
                    "오류": str(exc),
                    "로그": (
                        self._context.paths.log_path
                    ),
                },
            )

            raise FactoryExecutionError(
                str(exc)
            ) from exc

    def _prepare_timeline(
        self,
    ) -> None:
        paths = self._context.paths
        options = self._context.options

        should_generate = (
            options.rebuild_timeline
            or not paths.source_timeline.exists()
        )

        if not should_generate:
            return

        self._emit(
            FactoryEventType.DIRECTOR_STARTED,
            "실행",
            {
                "단계": (
                    "Director Timeline 생성"
                ),
                "에피소드": paths.episode_id,
            },
        )

        generated_path = build_episode_timeline(
            root_dir=paths.root_dir,
            episode_id=paths.episode_id,
        )

        if (
            generated_path.resolve()
            != paths.source_timeline.resolve()
        ):
            raise DirectorExecutionError(
                "Director 출력 경로가 예상 경로와 "
                "다릅니다.\n"
                f"예상: {paths.source_timeline}\n"
                f"실제: {generated_path}"
            )

        self._context.timeline_generated = True

        self._emit(
            FactoryEventType.DIRECTOR_COMPLETED,
            "완료",
            {
                "단계": (
                    "Director Timeline 생성"
                ),
                "출력": generated_path,
            },
        )

    def _validate_timeline(
        self,
        *,
        stage_name: str,
    ) -> None:
        timeline, summary = (
            load_and_validate_timeline(
                self._context.paths.source_timeline
            )
        )

        expected_episode = (
            self._context.paths.episode_id.lower()
        )

        if (
            summary.episode_id.strip().lower()
            != expected_episode
        ):
            raise TimelineValidationError(
                "timeline episodeId가 요청한 "
                "에피소드와 일치하지 않습니다.\n"
                f"요청: {expected_episode}\n"
                f"timeline: {summary.episode_id}"
            )

        self._context.timeline = timeline
        self._context.title = summary.title
        self._context.scene_count = (
            summary.scene_count
        )
        self._context.total_duration = (
            summary.total_duration
        )
        self._context.fps = summary.fps
        self._context.width = summary.width
        self._context.height = summary.height

        self._emit(
            FactoryEventType.TIMELINE_VALIDATED,
            "완료",
            {
                "단계": stage_name,
                "제목": summary.title,
                "장면": (
                    f"{summary.scene_count}개"
                ),
                "길이": (
                    f"{summary.total_duration:.3f}초"
                ),
                "화면": (
                    f"{summary.width}x"
                    f"{summary.height} "
                    f"/ {summary.fps}fps"
                ),
            },
        )

    def _generate_tts_and_sync_duration(
        self,
    ) -> None:
        tts_dir = (
            self._context.paths.root_dir
            / "projects"
            / "tts"
        )

        if not tts_dir.exists():
            raise FactoryExecutionError(
                "TTS 모듈 폴더를 찾을 수 없습니다.\n"
                f"경로: {tts_dir}"
            )

        if str(tts_dir) not in sys.path:
            sys.path.insert(
                0,
                str(tts_dir),
            )

        try:
            from tts_batch import (
                TTSBatchError,
                TimelineTTSBatchGenerator,
            )
            from tts_config import (
                TTSConfig,
                TTSConfigError,
            )
            from tts_engine import (
                EdgeTTSEngine,
                TTSEngineError,
            )

        except ImportError as exc:
            raise FactoryExecutionError(
                "TTS 모듈을 불러오지 "
                "못했습니다.\n"
                f"경로: {tts_dir}\n"
                f"원인: {exc}"
            ) from exc

        self._emit(
            FactoryEventType.DIRECTOR_STARTED,
            "실행",
            {
                "단계": (
                    "TTS 생성 및 Duration Sync"
                ),
                "Timeline": (
                    self._context.paths.source_timeline
                ),
            },
        )

        try:
            config = TTSConfig.from_environment()

            engine = EdgeTTSEngine(
                config=config,
            )

            generator = (
                TimelineTTSBatchGenerator(
                    engine=engine,
                )
            )

            result = generator.generate_sync(
                timeline_path=(
                    self._context.paths.source_timeline
                ),
                output_dir=(
                    self._context.paths.source_audio_dir
                ),
                sync_timeline=True,
            )

        except (
            TTSConfigError,
            TTSEngineError,
            TTSBatchError,
        ) as exc:
            raise FactoryExecutionError(
                "TTS 생성 또는 Duration Sync에 "
                "실패했습니다.\n"
                f"원인: {exc}"
            ) from exc

        if result.total_count <= 0:
            raise FactoryExecutionError(
                "생성된 TTS 장면이 없습니다."
            )

        if (
            result.total_count
            != self._context.scene_count
        ):
            raise FactoryExecutionError(
                "Timeline 장면 수와 TTS 파일 수가 "
                "일치하지 않습니다.\n"
                f"Timeline: "
                f"{self._context.scene_count}\n"
                f"TTS: {result.total_count}"
            )

        for audio_result in result.results:
            if not audio_result.output_path.exists():
                raise FactoryExecutionError(
                    "생성된 TTS 파일을 찾을 수 "
                    "없습니다.\n"
                    f"장면: {audio_result.scene_id}\n"
                    f"파일: "
                    f"{audio_result.output_path}"
                )

            if audio_result.file_size_bytes <= 0:
                raise FactoryExecutionError(
                    "TTS 파일의 크기가 "
                    "0입니다.\n"
                    f"장면: {audio_result.scene_id}"
                )

            if audio_result.duration_seconds <= 0:
                raise FactoryExecutionError(
                    "TTS 파일의 길이가 "
                    "0초 이하입니다.\n"
                    f"장면: {audio_result.scene_id}"
                )

        self._emit(
            FactoryEventType.DIRECTOR_COMPLETED,
            "완료",
            {
                "단계": (
                    "TTS 생성 및 Duration Sync"
                ),
                "전체": (
                    f"{result.total_count}개"
                ),
                "신규": (
                    f"{result.generated_count}개"
                ),
                "재사용": (
                    f"{result.reused_count}개"
                ),
                "길이": (
                    f"{result.total_duration:.3f}초"
                ),
            },
        )

    def _collect_and_sync_assets(
        self,
    ) -> None:
        if self._context.timeline is None:
            raise TimelineValidationError(
                "검증된 Timeline이 없습니다."
            )

        required_assets = collect_required_assets(
            self._context.timeline,
            episode_id=(
                self._context.paths.episode_id
            ),
        )

        self._context.required_assets = (
            required_assets
        )
        self._context.required_asset_count = len(
            required_assets
        )

        asset_text = (
            ", ".join(
                path.as_posix()
                for path in required_assets
            )
            if required_assets
            else "없음"
        )

        self._emit(
            FactoryEventType.ASSETS_DISCOVERED,
            "확인",
            {
                "단계": "필수 미디어",
                "개수": (
                    f"{len(required_assets)}개"
                ),
                "파일": asset_text,
            },
        )

        result = sync_episode_assets(
            episode_assets_dir=(
                self._context.paths.source_assets_dir
            ),
            public_assets_dir=(
                self._context.paths.public_assets_dir
            ),
            required_assets=required_assets,
        )

        self._context.copied_asset_count = (
            result.copied_count
        )

        self._emit(
            FactoryEventType.ASSETS_SYNCED,
            "완료",
            {
                "단계": (
                    "Assets 검증 및 Public 복사"
                ),
                "원본": result.source_dir,
                "대상": result.destination_dir,
                "복사": (
                    f"{result.copied_count}개"
                ),
            },
        )

    def _validate_audio_files(
        self,
    ) -> None:
        if self._context.timeline is None:
            raise TimelineValidationError(
                "검증된 Timeline이 없습니다."
            )

        scenes = self._context.timeline.get(
            "scenes",
            [],
        )

        if not isinstance(scenes, list):
            raise FactoryExecutionError(
                "Timeline scenes가 배열이 아닙니다."
            )

        audio_files: list[Path] = []

        for index, scene in enumerate(
            scenes,
            start=1,
        ):
            if not isinstance(scene, dict):
                raise FactoryExecutionError(
                    f"{index}번째 scene 형식이 "
                    "올바르지 않습니다."
                )

            raw_audio = scene.get("audio")

            if not isinstance(raw_audio, str):
                raise FactoryExecutionError(
                    f"{index}번째 scene에 "
                    "audio 경로가 없습니다."
                )

            audio_name = Path(raw_audio).name

            audio_path = (
                self._context.paths.source_audio_dir
                / audio_name
            )

            if not audio_path.exists():
                raise FactoryExecutionError(
                    "TTS 파일이 없습니다:\n"
                    f"{audio_path}"
                )

            if audio_path.stat().st_size <= 0:
                raise FactoryExecutionError(
                    "크기가 0인 TTS 파일입니다:\n"
                    f"{audio_path}"
                )

            audio_files.append(audio_path)

        if len(audio_files) != len(scenes):
            raise FactoryExecutionError(
                "Scene 수와 Audio 수가 "
                "일치하지 않습니다."
            )

    def _publish_episode(
        self,
    ) -> None:
        paths = self._context.paths

        paths.public_episode_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        copied_audio_count = 0

        for source_audio in sorted(
            paths.source_audio_dir.glob("*.mp3")
        ):
            destination_audio = (
                paths.public_audio_dir
                / source_audio.name
            )

            shutil.copy2(
                source_audio,
                destination_audio,
            )

            copied_audio_count += 1

        self._context.copied_audio_count = (
            copied_audio_count
        )

        timeline_data = self._load_source_timeline()

        self._rewrite_public_paths(
            timeline_data
        )

        paths.public_timeline.write_text(
            json.dumps(
                timeline_data,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        self._emit(
            FactoryEventType.TIMELINE_PUBLISHED,
            "완료",
            {
                "단계": (
                    "Remotion Episode 배포"
                ),
                "대상": (
                    paths.public_episode_dir
                ),
                "Timeline": (
                    paths.public_timeline
                ),
                "Assets": (
                    f"{self._context.copied_asset_count}개"
                ),
                "Audio": (
                    f"{copied_audio_count}개"
                ),
            },
        )

    def _load_source_timeline(
        self,
    ) -> dict[str, Any]:
        path = self._context.paths.source_timeline

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise FactoryExecutionError(
                "Timeline을 읽지 못했습니다.\n"
                f"파일: {path}\n"
                f"원인: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise FactoryExecutionError(
                "Timeline 최상위 데이터가 "
                "객체가 아닙니다."
            )

        return data

    def _rewrite_public_paths(
        self,
        timeline_data: dict[str, Any],
    ) -> None:
        episode_id = (
            self._context.paths.episode_id
        )

        scenes = timeline_data.get(
            "scenes",
            [],
        )

        if not isinstance(scenes, list):
            raise FactoryExecutionError(
                "Timeline scenes가 배열이 아닙니다."
            )

        for scene in scenes:
            if not isinstance(scene, dict):
                continue

            media = scene.get("media")

            if isinstance(media, dict):
                raw_src = media.get("src")

                if isinstance(raw_src, str):
                    media["src"] = (
                        f"{episode_id}/"
                        f"{Path(raw_src).name}"
                    )

            raw_audio = scene.get("audio")

            if isinstance(raw_audio, str):
                scene["audio"] = (
                    f"{episode_id}/"
                    f"{Path(raw_audio).name}"
                )

        timeline_data["episodeId"] = (
            episode_id
        )

    def _run_typecheck(
        self,
    ) -> None:
        if self._context.options.skip_typecheck:
            return

        typecheck_remotion(
            self._context.paths.remotion_dir
        )

        self._emit(
            FactoryEventType.TYPECHECK_COMPLETED,
            "완료",
            {
                "단계": "TypeScript 검사",
            },
        )

    def _render(
        self,
    ) -> None:
        render_episode(
            self._context.paths.remotion_dir,
            self._context.paths.output_path,
            episode_id=(
                self._context.paths.episode_id
            ),
        )

        self._emit(
            FactoryEventType.RENDER_COMPLETED,
            "완료",
            {
                "단계": "Remotion 렌더",
                "영상": (
                    self._context.paths.output_path
                ),
            },
        )

    def _save_log(
        self,
    ) -> None:
        log_path = self._context.paths.log_path

        log_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        log_path.write_text(
            json.dumps(
                self._context.build_log_payload(),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _build_result(
        self,
    ) -> FactoryRunResult:
        succeeded = (
            self._context.status
            in (
                "success",
                "validated",
            )
        )

        output_path: Path | None = None

        if self._context.status == "success":
            output_path = (
                self._context.paths.output_path
            )

        return FactoryRunResult(
            episode_id=(
                self._context.paths.episode_id
            ),
            status=self._context.status,
            succeeded=succeeded,
            timeline_generated=(
                self._context.timeline_generated
            ),
            scene_count=(
                self._context.scene_count
            ),
            total_duration=(
                self._context.total_duration
            ),
            required_asset_count=(
                self._context.required_asset_count
            ),
            copied_asset_count=(
                self._context.copied_asset_count
            ),
            output_path=output_path,
            log_path=(
                self._context.paths.log_path
            ),
            elapsed_seconds=(
                self._context.elapsed_seconds
            ),
        )

    def _emit(
        self,
        event_type: FactoryEventType,
        title: str,
        details: dict[str, object],
    ) -> None:
        self._reporter.emit(
            FactoryEvent(
                event_type=event_type,
                title=title,
                details=details,
            )
        )