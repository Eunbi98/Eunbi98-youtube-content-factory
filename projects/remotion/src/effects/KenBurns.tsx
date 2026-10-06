import React from 'react';
import {
	Easing,
	interpolate,
	useCurrentFrame,
} from 'remotion';

import type {CameraMotion} from '../types/timeline';
import {motionPresets} from './motionPresets';

type KenBurnsProps = {
	children: React.ReactNode;
	durationInFrames: number;
	motion?: CameraMotion;
};

const OVERSCAN_PERCENT = 2;

const roundValue = (
	value: number,
	decimalPlaces: number,
): number => {
	const multiplier = 10 ** decimalPlaces;

	return (
		Math.round(value * multiplier) /
		multiplier
	);
};

export const KenBurns: React.FC<
	KenBurnsProps
> = ({
	children,
	durationInFrames,
	motion = 'static',
}) => {
	const frame = useCurrentFrame();

	const preset =
		motionPresets[motion] ??
		motionPresets.static;

	const endFrame = Math.max(
		1,
		durationInFrames - 1,
	);

	const interpolationOptions = {
		extrapolateLeft: 'clamp' as const,
		extrapolateRight: 'clamp' as const,
		easing: Easing.inOut(
			Easing.cubic,
		),
	};

	const scaleRange =
		preset.scale ?? [1, 1];

	const xRange =
		preset.x ?? [0, 0];

	const yRange =
		preset.y ?? [0, 0];

	const scale = interpolate(
		frame,
		[0, endFrame],
		scaleRange,
		interpolationOptions,
	);

	const translateX = interpolate(
		frame,
		[0, endFrame],
		xRange,
		interpolationOptions,
	);

	const translateY = interpolate(
		frame,
		[0, endFrame],
		yRange,
		interpolationOptions,
	);

	const stableScale = roundValue(
		scale,
		4,
	);

	const stableTranslateX = roundValue(
		translateX,
		3,
	);

	const stableTranslateY = roundValue(
		translateY,
		3,
	);

	const transform = [
		`scale(${stableScale})`,
		`translate3d(${stableTranslateX}%, ${stableTranslateY}%, 0)`,
	].join(' ');

	return (
		<div
			style={{
				position: 'absolute',

				top: `-${OVERSCAN_PERCENT}%`,
				right: `-${OVERSCAN_PERCENT}%`,
				bottom: `-${OVERSCAN_PERCENT}%`,
				left: `-${OVERSCAN_PERCENT}%`,

				overflow: 'hidden',

				transform,

				transformOrigin:
					preset.transformOrigin ??
					'center center',

				willChange: 'transform',

				backfaceVisibility:
					'hidden',

				WebkitBackfaceVisibility:
					'hidden',
			}}
		>
			{children}
		</div>
	);
};