import React from 'react';

import {
	CalculateMetadataFunction,
	Composition,
	staticFile,
} from 'remotion';

import {
	EpisodeComposition,
	type EpisodeCompositionProps,
} from './compositions/EpisodeComposition';

import {
	QuizComposition,
	type QuizCompositionProps,
} from './quiz/QuizComposition';

import type {
	EpisodeTimeline,
} from './types/timeline';

import {
	validateTimeline,
} from './utils/timeline';

const mysteryFallbackTimeline: EpisodeTimeline = {
	episodeId: 'ep008',
	title: 'Timeline Loading',
	fps: 30,
	width: 1080,
	height: 1920,
	totalDuration: 1,
	theme: {
		backgroundColor: '#000000',
		titleColor: '#7CFFB2',
		captionColor: '#FFFFFF',
		accentColor: '#7CFFB2',
	},
	scenes: [
		{
			id: 'scene_loading',
			start: 0,
			duration: 1,
			caption:
				'Timeline loading...',
			backgroundColor: '#000000',
			media: {
				type: 'color',
			},
			cameraMotion: 'static',
			transition: 'fade',
			transitionDuration: 0.3,
			overlay: 'none',
		},
	],
};

const quizFallbackTimeline: EpisodeTimeline = {
	version: '8.1',
	episodeId: 'ep010',
	channel: 'quiz',
	title: 'Quiz Timeline Loading',
	fps: 30,
	width: 1080,
	height: 1920,
	totalDuration: 1,
	theme: {
		backgroundColor: '#6FB382',
		titleColor: '#214F2A',
		captionColor: '#214F2A',
		accentColor: '#F6D25B',
	},
	scenes: [
		{
			id: 'quiz_loading',
			sceneType: 'intro',
			start: 0,
			duration: 1,
			title: '오늘의 퀴즈',
			caption:
				'Quiz Timeline loading...',
			backgroundColor: '#6FB382',
			media: {
				type: 'color',
			},
			cameraMotion: 'static',
			transition: 'fade',
			transitionDuration: 0.3,
			overlay: 'none',
		},
	],
};

const normalizeEpisodeId = (
	rawEpisodeId: string | undefined,
	fallbackEpisodeId: string,
): string => {
	const normalized = rawEpisodeId
		?.trim()
		.toLowerCase();

	if (!normalized) {
		return fallbackEpisodeId;
	}

	if (!/^ep\d{3,}$/.test(normalized)) {
		throw new Error(
			`Invalid episodeId: ${rawEpisodeId}`,
		);
	}

	return normalized;
};

const loadTimeline = async (
	episodeId: string,
	abortSignal: AbortSignal,
): Promise<EpisodeTimeline> => {
	const timelinePath =
		`${episodeId}/timeline.json`;

	const response = await fetch(
		staticFile(timelinePath),
		{
			signal: abortSignal,
			cache: 'no-store',
		},
	);

	if (!response.ok) {
		throw new Error(
			`Failed to load ${timelinePath}: ` +
				`${response.status} ` +
				`${response.statusText}`,
		);
	}

	const rawTimeline: unknown =
		await response.json();

	const timeline =
		validateTimeline(rawTimeline);

	if (
		timeline.episodeId
			.trim()
			.toLowerCase() !== episodeId
	) {
		throw new Error(
			'Timeline episodeId mismatch: ' +
				`expected ${episodeId}, ` +
				`received ${timeline.episodeId}`,
		);
	}

	return timeline;
};

const calculateEpisodeMetadata: CalculateMetadataFunction<
	EpisodeCompositionProps
> = async ({
	props,
	abortSignal,
}) => {
	const episodeId = normalizeEpisodeId(
		props.episodeId,
		'ep008',
	);

	const timeline = await loadTimeline(
		episodeId,
		abortSignal,
	);

	return {
		durationInFrames: Math.max(
			1,
			Math.ceil(
				timeline.totalDuration *
					timeline.fps,
			),
		),

		fps: timeline.fps,
		width: timeline.width,
		height: timeline.height,

		props: {
			episodeId,
			timeline,
		},
	};
};

const calculateQuizMetadata: CalculateMetadataFunction<
	QuizCompositionProps
> = async ({
	props,
	abortSignal,
}) => {
	const episodeId = normalizeEpisodeId(
		props.episodeId,
		'ep010',
	);

	const timeline = await loadTimeline(
		episodeId,
		abortSignal,
	);

	if (
		timeline.channel &&
		timeline.channel !== 'quiz'
	) {
		throw new Error(
			`QuizEpisode requires channel=quiz. ` +
				`Received: ${timeline.channel}`,
		);
	}

	return {
		durationInFrames: Math.max(
			1,
			Math.ceil(
				timeline.totalDuration *
					timeline.fps,
			),
		),

		fps: timeline.fps,
		width: timeline.width,
		height: timeline.height,

		props: {
			episodeId,
			timeline,
		},
	};
};

const CompatibleEpisodeComposition =
	EpisodeComposition as React.ComponentType<
		EpisodeCompositionProps
	>;

const CompatibleQuizComposition =
	QuizComposition as React.ComponentType<
		QuizCompositionProps
	>;

export const RemotionRoot: React.FC = () => {
	return (
		<>
			<Composition
				id="Episode"
				component={
					CompatibleEpisodeComposition
				}
				durationInFrames={
					Math.max(
						1,
						Math.ceil(
							mysteryFallbackTimeline
								.totalDuration *
								mysteryFallbackTimeline
									.fps,
						),
					)
				}
				fps={
					mysteryFallbackTimeline.fps
				}
				width={
					mysteryFallbackTimeline.width
				}
				height={
					mysteryFallbackTimeline.height
				}
				defaultProps={{
					episodeId: 'ep008',
					timeline:
						mysteryFallbackTimeline,
				}}
				calculateMetadata={
					calculateEpisodeMetadata
				}
			/>

			<Composition
				id="QuizEpisode"
				component={
					CompatibleQuizComposition
				}
				durationInFrames={
					Math.max(
						1,
						Math.ceil(
							quizFallbackTimeline
								.totalDuration *
								quizFallbackTimeline
									.fps,
						),
					)
				}
				fps={
					quizFallbackTimeline.fps
				}
				width={
					quizFallbackTimeline.width
				}
				height={
					quizFallbackTimeline.height
				}
				defaultProps={{
					episodeId: 'ep010',
					timeline:
						quizFallbackTimeline,
				}}
				calculateMetadata={
					calculateQuizMetadata
				}
			/>
		</>
	);
};