import React from 'react';
import {AbsoluteFill} from 'remotion';

import {SceneTransition} from '../effects/SceneTransition';
import type {TimelineScene} from '../types/timeline';
import {CaptionLayer} from './CaptionLayer';
import {OverlayLayer} from './OverlayLayer';
import {VisualLayer} from './VisualLayer';

type SceneRendererProps = {
	scene: TimelineScene;

	durationInFrames: number;
	transitionDurationInFrames: number;

	isFirstScene: boolean;
	isLastScene: boolean;

	captionColor?: string;
};

export const SceneRenderer: React.FC<
	SceneRendererProps
> = ({
	scene,
	durationInFrames,
	transitionDurationInFrames,
	isFirstScene,
	isLastScene,
	captionColor,
}) => {
	return (
		<SceneTransition
			durationInFrames={
				durationInFrames
			}
			transitionDurationInFrames={
				transitionDurationInFrames
			}
			transition={
				scene.transition ?? 'fade'
			}
			isFirstScene={isFirstScene}
			isLastScene={isLastScene}
		>
			<AbsoluteFill
				style={{
					backgroundColor:
						scene.backgroundColor ??
						'#000000',
				}}
			>
				<VisualLayer
					scene={scene}
					durationInFrames={
						durationInFrames
					}
				/>

				<OverlayLayer
					scene={scene}
				/>

				<CaptionLayer
					caption={scene.caption}
					color={captionColor}
				/>
			</AbsoluteFill>
		</SceneTransition>
	);
};