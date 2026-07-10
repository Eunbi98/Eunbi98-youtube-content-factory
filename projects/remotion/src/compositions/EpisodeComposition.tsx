import React from 'react';
import {
	AbsoluteFill,
	Sequence,
} from 'remotion';

import {SceneRenderer} from '../components/SceneRenderer';
import {TitleLayer} from '../components/TitleLayer';
import {ep005Theme} from '../theme/ep005Theme';
import type {EpisodeTimeline} from '../types/timeline';
import {
	getSceneDurationFrames,
	getSceneStartFrame,
	secondsToFrames,
} from '../utils/timeline';

export type EpisodeCompositionProps = {
	timeline: EpisodeTimeline;
};

export const EpisodeComposition: React.FC<
	EpisodeCompositionProps
> = ({timeline}) => {
	const fps = timeline.fps;

	const backgroundColor =
		timeline.theme?.backgroundColor ??
		ep005Theme.backgroundColor;

	const titleColor =
		timeline.theme?.titleColor ??
		ep005Theme.titleColor;

	const captionColor =
		timeline.theme?.captionColor ??
		ep005Theme.captionColor;

	return (
		<AbsoluteFill
			style={{
				backgroundColor,
				fontFamily: ep005Theme.fontFamily,
				overflow: 'hidden',
			}}
		>
			{/* 장면 레이어 */}
			{timeline.scenes.map((scene, index) => {
				const from =
					getSceneStartFrame(scene, fps);

				const durationInFrames =
					getSceneDurationFrames(
						scene,
						fps,
					);

				const transitionDuration =
					secondsToFrames(
						scene.transitionDuration ??
							0.25,
						fps,
					);

				return (
					<Sequence
						key={scene.id}
						from={from}
						durationInFrames={
							durationInFrames
						}
						name={scene.id}
					>
						<SceneRenderer
							scene={scene}
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
								timeline.scenes
									.length -
									1
							}
							captionColor={
								captionColor
							}
						/>
					</Sequence>
				);
			})}

			{/* 제목은 항상 장면 위에 표시 */}
			<TitleLayer
				title={timeline.title}
				color={titleColor}
			/>
		</AbsoluteFill>
	);
};