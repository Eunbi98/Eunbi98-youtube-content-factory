import React, {useMemo} from 'react';
import {
	AbsoluteFill,
	Easing,
	interpolate,
	useCurrentFrame,
} from 'remotion';

export type SceneTransitionPreset =
	| 'cut'
	| 'fade'
	| 'slide'
	| 'zoom';

export type SceneTransitionDirection =
	| 'left'
	| 'right'
	| 'up'
	| 'down';

export type SceneTransitionConfig = {
	preset?: SceneTransitionPreset;

	durationInFrames?: number;

	direction?: SceneTransitionDirection;

	/**
	 * 화면 크기를 기준으로 한 이동 비율입니다.
	 *
	 * 0.12 = 화면의 12%
	 */
	slideDistance?: number;

	/**
	 * Zoom Transition 시작 배율입니다.
	 *
	 * 0.96 = 96%에서 100%로 확대
	 */
	zoomInScale?: number;

	/**
	 * 종료 효과를 사용할 경우의 배율입니다.
	 */
	zoomOutScale?: number;

	enableEnter?: boolean;
	enableExit?: boolean;
};

type SceneTransitionProps = {
	children: React.ReactNode;

	durationInFrames: number;

	transition?: SceneTransitionConfig;

	isLastScene?: boolean;

	className?: string;
	style?: React.CSSProperties;
};

type TransitionStyle = {
	opacity: number;
	transform: string;
};

const DEFAULT_TRANSITION: Required<SceneTransitionConfig> = {
	preset: 'cut',

	durationInFrames: 9,

	direction: 'left',

	slideDistance: 0.12,

	zoomInScale: 0.96,
	zoomOutScale: 1.04,

	enableEnter: true,
	enableExit: false,
};

const CLAMP = {
	extrapolateLeft: 'clamp' as const,
	extrapolateRight: 'clamp' as const,
};

const getEnterSlidePosition = (
	direction: SceneTransitionDirection,
	progress: number,
	distance: number,
): {
	x: number;
	y: number;
} => {
	const remainingDistance =
		(1 - progress) * distance * 100;

	switch (direction) {
		case 'right':
			return {
				x: -remainingDistance,
				y: 0,
			};

		case 'up':
			return {
				x: 0,
				y: remainingDistance,
			};

		case 'down':
			return {
				x: 0,
				y: -remainingDistance,
			};

		case 'left':
		default:
			return {
				x: remainingDistance,
				y: 0,
			};
	}
};

const getExitSlidePosition = (
	direction: SceneTransitionDirection,
	progress: number,
	distance: number,
): {
	x: number;
	y: number;
} => {
	const movedDistance =
		progress * distance * 100;

	switch (direction) {
		case 'right':
			return {
				x: movedDistance,
				y: 0,
			};

		case 'up':
			return {
				x: 0,
				y: -movedDistance,
			};

		case 'down':
			return {
				x: 0,
				y: movedDistance,
			};

		case 'left':
		default:
			return {
				x: -movedDistance,
				y: 0,
			};
	}
};

const getEnterStyle = ({
	preset,
	progress,
	direction,
	slideDistance,
	zoomInScale,
}: {
	preset: SceneTransitionPreset;
	progress: number;
	direction: SceneTransitionDirection;
	slideDistance: number;
	zoomInScale: number;
}): TransitionStyle => {
	switch (preset) {
		case 'fade':
			return {
				opacity: progress,
				transform:
					'translate3d(0, 0, 0) scale(1)',
			};

		case 'slide': {
			const position =
				getEnterSlidePosition(
					direction,
					progress,
					slideDistance,
				);

			return {
				/*
				 * Slide에서 완전히 투명하게 시작하면
				 * 검은 화면이 강하게 보이므로
				 * 약간의 투명도만 사용합니다.
				 */
				opacity: interpolate(
					progress,
					[0, 1],
					[0.82, 1],
					CLAMP,
				),

				transform: `translate3d(${position.x}%, ${position.y}%, 0) scale(1.015)`,
			};
		}

		case 'zoom': {
			const scale = interpolate(
				progress,
				[0, 1],
				[zoomInScale, 1],
				CLAMP,
			);

			return {
				opacity: interpolate(
					progress,
					[0, 1],
					[0.72, 1],
					CLAMP,
				),

				transform: `translate3d(0, 0, 0) scale(${scale})`,
			};
		}

		case 'cut':
		default:
			return {
				opacity: 1,
				transform:
					'translate3d(0, 0, 0) scale(1)',
			};
	}
};

const getExitStyle = ({
	preset,
	progress,
	direction,
	slideDistance,
	zoomOutScale,
}: {
	preset: SceneTransitionPreset;
	progress: number;
	direction: SceneTransitionDirection;
	slideDistance: number;
	zoomOutScale: number;
}): TransitionStyle => {
	switch (preset) {
		case 'fade':
			return {
				opacity: 1 - progress,
				transform:
					'translate3d(0, 0, 0) scale(1)',
			};

		case 'slide': {
			const position =
				getExitSlidePosition(
					direction,
					progress,
					slideDistance,
				);

			return {
				opacity: interpolate(
					progress,
					[0, 1],
					[1, 0.82],
					CLAMP,
				),

				transform: `translate3d(${position.x}%, ${position.y}%, 0) scale(1.015)`,
			};
		}

		case 'zoom': {
			const scale = interpolate(
				progress,
				[0, 1],
				[1, zoomOutScale],
				CLAMP,
			);

			return {
				opacity: interpolate(
					progress,
					[0, 1],
					[1, 0.72],
					CLAMP,
				),

				transform: `translate3d(0, 0, 0) scale(${scale})`,
			};
		}

		case 'cut':
		default:
			return {
				opacity: 1,
				transform:
					'translate3d(0, 0, 0) scale(1)',
			};
	}
};

export const SceneTransition: React.FC<
	SceneTransitionProps
> = ({
	children,
	durationInFrames,
	transition,
	isLastScene = false,
	className,
	style,
}) => {
	const frame = useCurrentFrame();

	const config = useMemo<
		Required<SceneTransitionConfig>
	>(() => {
		return {
			...DEFAULT_TRANSITION,
			...transition,
		};
	}, [transition]);

	const safeSceneDuration = Math.max(
		1,
		Math.floor(durationInFrames),
	);

	const maximumTransitionDuration =
		Math.max(
			1,
			Math.floor(
				safeSceneDuration * 0.35,
			),
		);

	const safeTransitionDuration = Math.max(
		1,
		Math.min(
			Math.floor(
				config.durationInFrames,
			),
			maximumTransitionDuration,
		),
	);

	const enterEnabled =
		config.preset !== 'cut' &&
		config.enableEnter;

	const exitEnabled =
		config.preset !== 'cut' &&
		config.enableExit &&
		!isLastScene;

	const enterProgress = enterEnabled
		? interpolate(
				frame,
				[0, safeTransitionDuration],
				[0, 1],
				{
					...CLAMP,

					easing: Easing.out(
						Easing.cubic,
					),
				},
			)
		: 1;

	const exitStartFrame = Math.max(
		0,
		safeSceneDuration -
			safeTransitionDuration,
	);

	const exitProgress = exitEnabled
		? interpolate(
				frame,
				[
					exitStartFrame,
					safeSceneDuration - 1,
				],
				[0, 1],
				{
					...CLAMP,

					easing: Easing.in(
						Easing.cubic,
					),
				},
			)
		: 0;

	const enterStyle = getEnterStyle({
		preset: config.preset,
		progress: enterProgress,
		direction: config.direction,
		slideDistance:
			config.slideDistance,
		zoomInScale:
			config.zoomInScale,
	});

	const exitStyle = getExitStyle({
		preset: config.preset,
		progress: exitProgress,
		direction: config.direction,
		slideDistance:
			config.slideDistance,
		zoomOutScale:
			config.zoomOutScale,
	});

	const opacity =
		exitEnabled && exitProgress > 0
			? exitStyle.opacity
			: enterStyle.opacity;

	const transform =
		exitEnabled && exitProgress > 0
			? exitStyle.transform
			: enterStyle.transform;

	return (
		<AbsoluteFill
			className={className}
			style={{
				opacity,
				transform,

				transformOrigin:
					'center center',

				overflow: 'hidden',

				willChange:
					'transform, opacity',

				backfaceVisibility:
					'hidden',

				/*
				 * GPU 합성을 유도해 Preview와
				 * 렌더 결과의 차이를 줄입니다.
				 */
				perspective: 1000,

				...style,
			}}
		>
			{children}
		</AbsoluteFill>
	);
};