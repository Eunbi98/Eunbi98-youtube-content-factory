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

import type {
	EpisodeTimeline,
} from './types/timeline';

import {
	validateTimeline,
} from './utils/timeline';

const fallbackTimeline: EpisodeTimeline = {
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

			backgroundColor:
				'#000000',

			media: {
				type: 'color',
			},

			cameraMotion:
				'static',

			transition:
				'fade',

			transitionDuration:
				0.3,

			overlay:
				'none',
		},
	],
};

const normalizeEpisodeId = (
	rawEpisodeId: string | undefined,
): string => {
	const normalized =
		rawEpisodeId
			?.trim()
			.toLowerCase();

	if (!normalized) {
		return 'ep008';
	}

	if (!/^ep\d{3,}$/.test(normalized)) {
		throw new Error(
			`Invalid episodeId: ${rawEpisodeId}`,
		);
	}

	return normalized;
};

const calculateMetadata: CalculateMetadataFunction<
	EpisodeCompositionProps
> = async ({
	props,
	abortSignal,
}) => {
	const episodeId =
		normalizeEpisodeId(
			props.episodeId,
		);

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
			.toLowerCase() !==
		episodeId
	) {
		throw new Error(
			`Timeline episodeId mismatch: ` +
			`expected ${episodeId}, ` +
			`received ${timeline.episodeId}`,
		);
	}

	return {
		durationInFrames:
			Math.max(
				1,
				Math.ceil(
					timeline.totalDuration *
						timeline.fps,
				),
			),

		fps:
			timeline.fps,

		width:
			timeline.width,

		height:
			timeline.height,

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

export const RemotionRoot:
React.FC = () => {
	return (
		<Composition
			id="Episode"

			component={
				CompatibleEpisodeComposition
			}

			durationInFrames={
				fallbackTimeline.totalDuration *
				fallbackTimeline.fps
			}

			fps={
				fallbackTimeline.fps
			}

			width={
				fallbackTimeline.width
			}

			height={
				fallbackTimeline.height
			}

			defaultProps={{
				episodeId:
					fallbackTimeline.episodeId,

				timeline:
					fallbackTimeline,
			}}

			calculateMetadata={
				calculateMetadata
			}
		/>
	);
};