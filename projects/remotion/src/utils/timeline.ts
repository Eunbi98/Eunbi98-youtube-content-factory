import type {
	EpisodeTimeline,
	TimelineScene,
} from '../types/timeline';

export const secondsToFrames = (
	seconds: number,
	fps: number,
): number => {
	return Math.max(
		0,
		Math.round(seconds * fps),
	);
};

export const getSceneStartFrame = (
	scene: TimelineScene,
	fps: number,
): number => {
	return secondsToFrames(scene.start, fps);
};

export const getSceneDurationFrames = (
	scene: TimelineScene,
	fps: number,
): number => {
	return Math.max(
		1,
		secondsToFrames(scene.duration, fps),
	);
};

export const validateTimeline = (
	value: unknown,
): EpisodeTimeline => {
	if (
		typeof value !== 'object' ||
		value === null
	) {
		throw new Error(
			'timeline.json must contain an object.',
		);
	}

	const timeline =
		value as Partial<EpisodeTimeline>;

	if (
		!Array.isArray(timeline.scenes) ||
		timeline.scenes.length === 0
	) {
		throw new Error(
			'timeline.json must contain scenes.',
		);
	}

	if (
		typeof timeline.totalDuration !== 'number' ||
		timeline.totalDuration <= 0
	) {
		throw new Error(
			'totalDuration must be greater than zero.',
		);
	}

	return timeline as EpisodeTimeline;
};