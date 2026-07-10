import React from 'react';
import {AbsoluteFill} from 'remotion';

import {ep005Theme} from '../theme/ep005Theme';
import type {TimelineScene} from '../types/timeline';

type OverlayLayerProps = {
	scene: TimelineScene;
};

export const OverlayLayer: React.FC<
	OverlayLayerProps
> = ({scene}) => {
	const overlay =
		scene.overlay ?? 'cinematic';

	const opacity =
		scene.overlayOpacity ?? 1;

	if (overlay === 'none') {
		return null;
	}

	let background =
		'linear-gradient(180deg, rgba(0,0,0,0.18) 0%, rgba(0,0,0,0.02) 45%, rgba(0,0,0,0.70) 100%)';

	if (overlay === 'vignette') {
		background =
			'radial-gradient(circle at center, rgba(0,0,0,0) 40%, rgba(0,0,0,0.75) 100%)';
	}

	if (overlay === 'dark') {
		background =
			'rgba(0,0,0,0.42)';
	}

	return (
		<div
			style={{
				position: 'absolute',

				top: ep005Theme.visual.top,
				bottom: ep005Theme.visual.bottom,
				left: ep005Theme.visual.left,
				right: ep005Theme.visual.right,

				background,
				opacity,

				pointerEvents: 'none',
			}}
		/>
	);
};