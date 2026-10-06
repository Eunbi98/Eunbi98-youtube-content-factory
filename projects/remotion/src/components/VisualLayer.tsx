import React from 'react';
import {
	AbsoluteFill,
	OffthreadVideo,
	staticFile,
	useCurrentFrame,
	interpolate,
	Easing,
} from 'remotion';

import {KenBurns} from '../effects/KenBurns';
import {ep005Theme} from '../theme/ep005Theme';
import type {TimelineScene} from '../types/timeline';

type VisualLayerProps = {
	scene: TimelineScene;
	durationInFrames: number;
};

export const VisualLayer: React.FC<
	VisualLayerProps
> = ({
	scene,
	durationInFrames,
}) => {
	const frame = useCurrentFrame();
	const media = scene.media;

	const mediaStyle: React.CSSProperties = {
		position: 'absolute',
		inset: 0,
		width: '100%',
		height: '100%',
		display: 'block',
		objectFit: 'cover',
		objectPosition:
			media?.position ??
			'center center',
	};

	const renderMedia = () => {
		if (
			!media ||
			media.type === 'color' ||
			!media.src
		) {
			return (
				<AbsoluteFill
					style={{
						backgroundColor:
							scene.backgroundColor ??
							'#111111',
						backgroundImage:
							'radial-gradient(circle at center, rgba(255,255,255,0.12), rgba(0,0,0,0) 60%)',
					}}
				/>
			);
		}

		if (media.type === 'video') {
			return (
				<OffthreadVideo
					src={staticFile(media.src)}
					style={mediaStyle}
					volume={0.1}
				/>
			);
		}

		return (
			<AbsoluteFill
				style={{
					backgroundImage:
						`url("${staticFile(media.src)}")`,
					backgroundPosition:
						media.position ??
						'center center',
					backgroundRepeat: 'no-repeat',
					backgroundSize: 'cover',
				}}
			/>
		);
	};

	const visual = renderMedia();
	const isVideo = media?.type === 'video';
	const resolvedMotion =
		scene.cameraMotion ??
		(isVideo ? 'zoom_in' : 'static');

	const videoScale = isVideo
		? interpolate(
			frame,
			[0, Math.max(1, durationInFrames - 1)],
			[1, 1.08],
			{
				extrapolateLeft: 'clamp',
				extrapolateRight: 'clamp',
				easing: Easing.inOut(Easing.cubic),
			},
		)
		: 1;

	return (
		<div
			style={{
				position: 'absolute',
				top: ep005Theme.visual.top,
				bottom: ep005Theme.visual.bottom,
				left: ep005Theme.visual.left,
				right: ep005Theme.visual.right,
				overflow: 'hidden',
				backgroundColor:
					scene.backgroundColor ??
					'#111111',
				zIndex: 10,
			}}
		>
			<div
				style={{
					position: 'absolute',
					inset: 0,
					transform: isVideo
						? `scale(${videoScale})`
						: undefined,
					transformOrigin: 'center center',
					willChange: isVideo ? 'transform' : undefined,
				}}
			>
				<KenBurns
					durationInFrames={durationInFrames}
					motion={resolvedMotion}
				>
					{visual}
				</KenBurns>
			</div>
		</div>
	);
};
