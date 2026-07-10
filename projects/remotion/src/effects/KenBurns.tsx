import React from 'react';
import {
	interpolate,
	useCurrentFrame,
} from 'remotion';

import type {CameraMotion} from '../types/timeline';

type KenBurnsProps = {
	children: React.ReactNode;
	durationInFrames: number;
	motion?: CameraMotion;
};

type MotionState = {
	fromScale: number;
	toScale: number;
	fromX: number;
	toX: number;
	fromY: number;
	toY: number;
};

const getMotionState = (
	motion: CameraMotion,
): MotionState => {
	switch (motion) {
		case 'zoom_in':
			return {
				fromScale: 1,
				toScale: 1.1,
				fromX: 0,
				toX: 0,
				fromY: 0,
				toY: 0,
			};

		case 'zoom_out':
			return {
				fromScale: 1.1,
				toScale: 1,
				fromX: 0,
				toX: 0,
				fromY: 0,
				toY: 0,
			};

		case 'pan_left':
			return {
				fromScale: 1.08,
				toScale: 1.08,
				fromX: 4,
				toX: -4,
				fromY: 0,
				toY: 0,
			};

		case 'pan_right':
			return {
				fromScale: 1.08,
				toScale: 1.08,
				fromX: -4,
				toX: 4,
				fromY: 0,
				toY: 0,
			};

		case 'pan_up':
			return {
				fromScale: 1.08,
				toScale: 1.08,
				fromX: 0,
				toX: 0,
				fromY: 4,
				toY: -4,
			};

		case 'pan_down':
			return {
				fromScale: 1.08,
				toScale: 1.08,
				fromX: 0,
				toX: 0,
				fromY: -4,
				toY: 4,
			};

		case 'static':
		default:
			return {
				fromScale: 1,
				toScale: 1,
				fromX: 0,
				toX: 0,
				fromY: 0,
				toY: 0,
			};
	}
};

export const KenBurns: React.FC<
	KenBurnsProps
> = ({
	children,
	durationInFrames,
	motion = 'static',
}) => {
	const frame = useCurrentFrame();

	const state =
		getMotionState(motion);

	const endFrame = Math.max(
		1,
		durationInFrames - 1,
	);

	const scale = interpolate(
		frame,
		[0, endFrame],
		[state.fromScale, state.toScale],
		{
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		},
	);

	const translateX = interpolate(
		frame,
		[0, endFrame],
		[state.fromX, state.toX],
		{
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		},
	);

	const translateY = interpolate(
		frame,
		[0, endFrame],
		[state.fromY, state.toY],
		{
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		},
	);

	return (
		<div
			style={{
				position: 'absolute',
				inset: '-3%',
				transform: [
					`translate3d(${translateX}%, ${translateY}%, 0)`,
					`scale(${scale})`,
				].join(' '),
				transformOrigin: 'center center',
				willChange: 'transform',
			}}
		>
			{children}
		</div>
	);
};