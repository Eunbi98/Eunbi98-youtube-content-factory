import React from 'react';

import {
	AbsoluteFill,
	Audio,
	Sequence,
	staticFile,
} from 'remotion';

import {
	SceneRenderer,
} from '../components/SceneRenderer';

import {
	TitleLayer,
} from '../components/TitleLayer';

import {
	ep005Theme,
} from '../theme/ep005Theme';

import type {
	EpisodeTimeline,
} from '../types/timeline';

import {
	getSceneDurationFrames,
	getSceneStartFrame,
	secondsToFrames,
} from '../utils/timeline';


export type EpisodeCompositionProps = {
	episodeId: string;
	timeline: EpisodeTimeline;
};


const DEFAULT_CROSSFADE_SECONDS =
	1.2;

const MAX_CROSSFADE_SECONDS =
	1.8;


const resolveTransitionSeconds = (
	timelineValue:
		number |
		undefined,
): number => {
	const requested =
		timelineValue ??
		DEFAULT_CROSSFADE_SECONDS;

	return Math.min(
		MAX_CROSSFADE_SECONDS,
		Math.max(
			DEFAULT_CROSSFADE_SECONDS,
			requested,
		),
	);
};


export const EpisodeComposition:
React.FC<
	EpisodeCompositionProps
> = ({
	timeline,
}) => {
	const fps =
		timeline.fps;

	const backgroundColor =
		timeline.theme
			?.backgroundColor ??
		ep005Theme.backgroundColor;

	const titleColor =
		timeline.theme
			?.titleColor ??
		ep005Theme.titleColor;

	const captionColor =
		timeline.theme
			?.captionColor ??
		ep005Theme.captionColor;

	return (
		<AbsoluteFill
			style={{
				backgroundColor,

				fontFamily:
					ep005Theme
						.fontFamily,

				overflow:
					'hidden',
			}}
		>
			{timeline.scenes.map(
				(scene, index) => {
					const previousScene =
						index > 0
							? timeline
									.scenes[
									index - 1
								]
							: undefined;

					const from =
						getSceneStartFrame(
							scene,
							fps,
						);

					const durationInFrames =
						getSceneDurationFrames(
							scene,
							fps,
						);

					const transitionSeconds =
						resolveTransitionSeconds(
							scene
								.transitionDuration,
						);

					const transitionDuration =
						secondsToFrames(
							transitionSeconds,
							fps,
						);

					return (
						<Sequence
							key={
								scene.id
							}
							from={from}
							durationInFrames={
								durationInFrames
							}
							name={
								scene.id
							}
						>
							<SceneRenderer
								scene={
									scene
								}
								previousScene={
									previousScene
								}
								durationInFrames={
									durationInFrames
								}
								transitionDurationInFrames={
									transitionDuration
								}
								isFirstScene={
									index === 0
								}
								isLastScene={
									index ===
									timeline
										.scenes
										.length -
										1
								}
								captionColor={
									captionColor
								}
							/>

							{scene.audio ? (
								<Audio
									src={
										staticFile(
											scene.audio,
										)
									}
								/>
							) : null}
						</Sequence>
					);
				},
			)}

			<TitleLayer
				title={
					timeline.title
				}
				color={
					titleColor
				}
			/>
		</AbsoluteFill>
	);
};