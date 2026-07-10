import React from 'react';
import {
	interpolate,
	useCurrentFrame,
} from 'remotion';

import type {TransitionType} from '../types/timeline';

type SceneTransitionProps = {
	children: React.ReactNode;

	durationInFrames: number;
	transitionDurationInFrames: number;

	transition?: TransitionType;
	isFirstScene: boolean;
	isLastScene: boolean;
};

export const SceneTransition: React.FC<
	SceneTransitionProps
> = ({
	children,
	durationInFrames,
	transitionDurationInFrames,
	transition = 'fade',
	isFirstScene,
	isLastScene,
}) => {
	const frame = useCurrentFrame();

	if (transition === 'cut') {
		return (
			<div
				style={{
					position: 'absolute',
					inset: 0,
				}}
			>
				{children}
			</div>
		);
	}

	const transitionFrames = Math.max(
		1,
		Math.min(
			transitionDurationInFrames,
			Math.floor(durationInFrames / 2),
		),
	);

	const enterProgress = isFirstScene
		? 1
		: interpolate(
				frame,
				[0, transitionFrames],
				[0, 1],
				{
					extrapolateLeft: 'clamp',
					extrapolateRight: 'clamp',
				},
			);

	const exitProgress = isLastScene
		? 1
		: interpolate(
				frame,
				[
					durationInFrames -
						transitionFrames,
					durationInFrames - 1,
				],
				[1, 0],
				{
					extrapolateLeft: 'clamp',
					extrapolateRight: 'clamp',
				},
			);

	const opacity = Math.min(
		enterProgress,
		exitProgress,
	);

	let transform = 'none';

	if (transition === 'slide_left') {
		const translateX = interpolate(
			enterProgress,
			[0, 1],
			[8, 0],
		);

		transform =
			`translateX(${translateX}%)`;
	}

	if (transition === 'slide_right') {
		const translateX = interpolate(
			enterProgress,
			[0, 1],
			[-8, 0],
		);

		transform =
			`translateX(${translateX}%)`;
	}

	if (transition === 'zoom') {
		const scale = interpolate(
			enterProgress,
			[0, 1],
			[1.08, 1],
		);

		transform = `scale(${scale})`;
	}

	return (
		<div
			style={{
				position: 'absolute',
				inset: 0,
				opacity,
				transform,
				willChange:
					'opacity, transform',
			}}
		>
			{children}
		</div>
	);
};