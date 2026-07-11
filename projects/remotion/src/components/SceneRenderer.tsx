import React from 'react';

import {
	AbsoluteFill,
	Easing,
	interpolate,
	useCurrentFrame,
} from 'remotion';

import {
	SceneTransition,
	type SceneTransitionConfig,
} from '../effects/SceneTransition';

import type {
	TimelineScene,
	TransitionType,
} from '../types/timeline';

import {
	CaptionLayer,
} from './CaptionLayer';

import {
	OverlayLayer,
} from './OverlayLayer';

import {
	VisualLayer,
} from './VisualLayer';


type SceneRendererProps = {
	scene: TimelineScene;
	previousScene?: TimelineScene;

	durationInFrames: number;
	transitionDurationInFrames: number;

	isFirstScene: boolean;
	isLastScene: boolean;

	captionColor: string;
};


type PreviousSceneLayerProps = {
	scene: TimelineScene;
	transitionDurationInFrames: number;
};


const CLAMP = {
	extrapolateLeft:
		'clamp' as const,

	extrapolateRight:
		'clamp' as const,
};


const PreviousSceneLayer:
React.FC<
	PreviousSceneLayerProps
> = ({
	scene,
	transitionDurationInFrames,
}) => {
	const frame =
		useCurrentFrame();

	const safeTransitionDuration =
		Math.max(
			1,
			Math.floor(
				transitionDurationInFrames,
			),
		);

	const opacity =
		interpolate(
			frame,
			[
				0,
				safeTransitionDuration,
			],
			[
				1,
				0,
			],
			{
				...CLAMP,

				easing:
					Easing.inOut(
						Easing.cubic,
					),
			},
		);

	return (
		<AbsoluteFill
			style={{
				opacity,
				zIndex: 0,
			}}
		>
			<VisualLayer
				scene={scene}
				durationInFrames={
					safeTransitionDuration
				}
			/>

			<OverlayLayer
				scene={scene}
			/>
		</AbsoluteFill>
	);
};


const createTransitionConfig = (
	transition:
		TransitionType |
		undefined,

	durationInFrames:
		number,
): SceneTransitionConfig => {
	const safeDuration =
		Math.max(
			1,
			Math.floor(
				durationInFrames,
			),
		);

	switch (
		transition ?? 'fade'
	) {
		case 'slide_left':
			return {
				preset: 'slide',
				durationInFrames:
					safeDuration,
				direction: 'left',
				slideDistance: 0.08,
				enableEnter: true,
				enableExit: false,
			};

		case 'slide_right':
			return {
				preset: 'slide',
				durationInFrames:
					safeDuration,
				direction: 'right',
				slideDistance: 0.08,
				enableEnter: true,
				enableExit: false,
			};

		case 'zoom':
			return {
				preset: 'zoom',
				durationInFrames:
					safeDuration,
				zoomInScale: 0.98,
				zoomOutScale: 1.02,
				enableEnter: true,
				enableExit: false,
			};

		case 'cut':
			return {
				preset: 'cut',
				durationInFrames:
					safeDuration,
				enableEnter: false,
				enableExit: false,
			};

		case 'fade':
		default:
			return {
				preset: 'fade',
				durationInFrames:
					safeDuration,
				enableEnter: true,
				enableExit: false,
			};
	}
};


export const SceneRenderer:
React.FC<
	SceneRendererProps
> = ({
	scene,
	previousScene,

	durationInFrames,
	transitionDurationInFrames,

	isFirstScene,
	isLastScene,

	captionColor,
}) => {
	const safeDurationInFrames =
		Math.max(
			1,
			Math.floor(
				durationInFrames,
			),
		);

	const safeTransitionDuration =
		Math.max(
			1,
			Math.min(
				Math.floor(
					transitionDurationInFrames,
				),

				Math.floor(
					safeDurationInFrames *
						0.45,
				),
			),
		);

	const transitionConfig =
		createTransitionConfig(
			scene.transition,
			safeTransitionDuration,
		);

	const resolvedTransition:
	SceneTransitionConfig = {
		...transitionConfig,

		enableEnter:
			!isFirstScene &&
			transitionConfig
				.enableEnter,

		enableExit: false,
	};

	const shouldRenderPrevious =
		!isFirstScene &&
		Boolean(previousScene) &&
		resolvedTransition.preset !==
			'cut';

	return (
		<AbsoluteFill>
			{shouldRenderPrevious &&
			previousScene ? (
				<PreviousSceneLayer
					scene={
						previousScene
					}
					transitionDurationInFrames={
						safeTransitionDuration
					}
				/>
			) : null}

			<SceneTransition
				durationInFrames={
					safeDurationInFrames
				}
				transition={
					resolvedTransition
				}
				isLastScene={
					isLastScene
				}
				style={{
					zIndex: 1,
				}}
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
				</AbsoluteFill>
			</SceneTransition>

			{scene.caption ? (
				<CaptionLayer
					caption={
						scene.caption
					}
					color={
						captionColor
					}
					durationInFrames={
						safeDurationInFrames
					}
				/>
			) : null}
		</AbsoluteFill>
	);
};