from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

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
            },
        )

        try:
            self._prepare_timeline()
            self._validate_timeline()
            self._collect_and_sync_assets()

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
                            "Timeline과 Assets 검증 완료"
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

            self._publish_timeline()
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
                    "로그": (
                        self._context.paths.log_path
                    ),
                    "장면": (
                        f"{self._context.scene_count}개"
                    ),
                    "Assets": (
                        f"{self._context.copied_asset_count}개"
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
                "단계": "Director Timeline 생성",
                "에피소드": paths.episode_id,
            },
        )

        generated_path = build_episode_timeline(
            root_dir=paths.root_dir,
            episode_id=paths.episode_id,
        )

        if generated_path.resolve() != (
            paths.source_timeline.resolve()
        ):
            raise DirectorExecutionError(
                "Director 출력 경로가 예상 경로와 다릅니다. "
                f"예상: {paths.source_timeline}, "
                f"실제: {generated_path}"
            )

        self._context.timeline_generated = True

        self._emit(
            FactoryEventType.DIRECTOR_COMPLETED,
            "완료",
            {
                "단계": "Director Timeline 생성",
                "출력": generated_path,
            },
        )

    def _validate_timeline(
        self,
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
                "timeline episodeId가 요청한 에피소드와 "
                "일치하지 않습니다. "
                f"요청: {expected_episode}, "
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
                "단계": "Timeline 검증",
                "제목": summary.title,
                "장면": f"{summary.scene_count}개",
                "길이": (
                    f"{summary.total_duration:.2f}초"
                ),
                "화면": (
                    f"{summary.width}x{summary.height} "
                    f"/ {summary.fps}fps"
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
                "단계": "Assets 검증 및 복사",
                "원본": result.source_dir,
                "대상": result.destination_dir,
                "복사": (
                    f"{result.copied_count}개"
                ),
            },
        )

    def _publish_timeline(
        self,
    ) -> None:
        source = (
            self._context.paths.source_timeline
        )
        destination = (
            self._context.paths.public_timeline
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source,
            destination,
        )

        self._emit(
            FactoryEventType.TIMELINE_PUBLISHED,
            "완료",
            {
                "단계": "Remotion Timeline 복사",
                "대상": destination,
            },
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
        succeeded = self._context.status in (
            "success",
            "validated",
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
            scene_count=self._context.scene_count,
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
            log_path=self._context.paths.log_path,
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
