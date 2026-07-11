from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class FactoryEventType(str, Enum):
    PIPELINE_STARTED = "pipeline_started"
    DIRECTOR_STARTED = "director_started"
    DIRECTOR_COMPLETED = "director_completed"
    TIMELINE_VALIDATED = "timeline_validated"
    ASSETS_DISCOVERED = "assets_discovered"
    ASSETS_SYNCED = "assets_synced"
    TIMELINE_PUBLISHED = "timeline_published"
    TYPECHECK_COMPLETED = "typecheck_completed"
    RENDER_COMPLETED = "render_completed"
    VALIDATION_COMPLETED = "validation_completed"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"


@dataclass(frozen=True)
class FactoryEvent:
    event_type: FactoryEventType
    title: str
    details: Mapping[str, object]


class ConsoleEventReporter:
    def emit(
        self,
        event: FactoryEvent,
    ) -> None:
        if event.event_type == (
            FactoryEventType.PIPELINE_STARTED
        ):
            print("=" * 58)
            print(" YouTube Content Factory Release 6.2")
            print("=" * 58)
            self._print_details(event.details)
            return

        if event.event_type == (
            FactoryEventType.PIPELINE_COMPLETED
        ):
            print()
            print("=" * 58)
            print(" Factory Runner 완료")
            print("=" * 58)
            self._print_details(event.details)
            return

        if event.event_type == (
            FactoryEventType.PIPELINE_FAILED
        ):
            print()
            print("=" * 58)
            print(" Factory Runner 실패")
            print("=" * 58)
            self._print_details(event.details)
            return

        print()
        print(f"[{event.title}]")
        self._print_details(event.details)

    @staticmethod
    def _print_details(
        details: Mapping[str, object],
    ) -> None:
        for key, value in details.items():
            print(f"       {key}: {value}")
