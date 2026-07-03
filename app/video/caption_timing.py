from __future__ import annotations


def fit_caption_texts_to_duration(
    texts: list[str],
    duration: float,
    min_seconds: float = 1.5,
) -> list[str]:
    if not texts:
        return []

    max_count = max(1, int(duration // min_seconds))

    if len(texts) <= max_count:
        return texts

    if max_count == 1:
        return [texts[-1]]

    return texts[:max_count - 1] + [texts[-1]]


def build_caption_schedule(
    text_count: int,
    total_duration: float,
    default_seconds: float = 4,
    min_seconds: float = 1.5,
) -> list[tuple[float, float]]:
    if text_count <= 0 or total_duration <= 0:
        return []

    if text_count * default_seconds <= total_duration:
        schedule = []

        for index in range(text_count):
            start = index * default_seconds

            if index == text_count - 1:
                clip_duration = max(min_seconds, total_duration - start)
            else:
                clip_duration = default_seconds

            schedule.append((start, min(clip_duration, total_duration - start)))

        return schedule

    slot = max(min_seconds, total_duration / text_count)
    schedule = []
    start = 0.0

    for index in range(text_count):
        remaining_slots = text_count - index - 1
        remaining_time = total_duration - start

        if index == text_count - 1:
            clip_duration = max(min_seconds, remaining_time)
            start = max(0.0, total_duration - clip_duration)
        else:
            clip_duration = min(
                slot,
                max(min_seconds, remaining_time - (remaining_slots * min_seconds)),
            )

        schedule.append((start, min(clip_duration, total_duration - start)))
        start += clip_duration

    return schedule
