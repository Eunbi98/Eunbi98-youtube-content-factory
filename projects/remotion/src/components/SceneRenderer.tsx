import React from 'react';
import {AbsoluteFill} from 'remotion';

import {
	SceneTransition,
	type SceneTransitionConfig,
} from '../effects/SceneTransition';

import type {
	TimelineScene,
	TransitionType,
} from '../types/timeline';

import {CaptionLayer} from './CaptionLayer';
import {OverlayLayer} from './OverlayLayer';
import {VisualLayer} from './VisualLayer';

type SceneRendererProps = {
	scene: TimelineScene;

	durationInFrames: number;
	transitionDurationInFrames: number;

	isFirstScene: boolean;
	isLastScene: boolean;

	captionColor: string;
};

const createTransitionConfig = (
	transition: TransitionType | undefined,
	durationInFrames: number,
): SceneTransitionConfig => {
	const safeDuration = Math.max(
		1,
		Math.floor(durationInFrames),
	);

	switch (transition ?? 'cut') {
		case 'fade':
			return {
				preset: 'fade',

				durationInFrames:
					safeDuration,

				enableEnter: true,

				/*
				 * 현재 Sequence는 서로 겹치지 않으므로
				 * 종료 Fade를 사용하면 검은 화면이 생깁니다.
				 */
				enableExit: false,
			};

		case 'slide_left':
			return {
				preset: 'slide',

				durationInFrames:
					safeDuration,

				direction: 'left',

				/*
				 * 화면 전체를 이동시키지 않고
				 * 12%만 움직여 자연스럽게 보이게 합니다.
				 */
				slideDistance: 0.12,

				enableEnter: true,
				enableExit: false,
			};

		case 'slide_right':
			return {
				preset: 'slide',

				durationInFrames:
					safeDuration,

				direction: 'right',
				slideDistance: 0.12,

				enableEnter: true,
				enableExit: false,
			};

		case 'zoom':
			return {
				preset: 'zoom',

				durationInFrames:
					safeDuration,

				zoomInScale: 0.96,
				zoomOutScale: 1.04,

				enableEnter: true,
				enableExit: false,
			};

		case 'cut':
		default:
			return {
				preset: 'cut',

				durationInFrames:
					safeDuration,

				enableEnter: false,
				enableExit: false,
			};
	}
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
	const safeDurationInFrames = Math.max(
		1,
		Math.floor(durationInFrames),
	);

	const transitionConfig =
		createTransitionConfig(
			scene.transition,
			transitionDurationInFrames,
		);

	const resolvedTransition: SceneTransitionConfig =
		{
			...transitionConfig,

			/*
			 * 첫 장면은 처음부터 완전히 표시합니다.
			 */
			enableEnter:
				!isFirstScene &&
				transitionConfig.enableEnter,

			/*
			 * Sequence가 겹치지 않는 현재 구조에서는
			 * exit 효과를 비활성화합니다.
			 */
			enableExit: false,
		};

	return (
		<AbsoluteFill
			style={{
				overflow: 'hidden',
			}}
		>
			<SceneTransition
				durationInFrames={
					safeDurationInFrames
				}
				transition={
					resolvedTransition
				}
				isLastScene={isLastScene}
			>
				<AbsoluteFill>
					<VisualLayer
						scene={scene}
						durationInFrames={
							safeDurationInFrames
						}
					/>

					<OverlayLayer
						scene={scene}
					/>

					{scene.caption ? (
						<CaptionLayer
							caption={
								scene.caption
							}
							color={
								captionColor
							}
						/>
					) : null}
				</AbsoluteFill>
			</SceneTransition>
		</AbsoluteFill>
	);
};