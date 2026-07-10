import React from 'react';

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
		ep005Theme.overlay.cinematic;

	if (overlay === 'vignette') {
		background =
			ep005Theme.overlay.vignette;
	}

	if (overlay === 'dark') {
		background =
			ep005Theme.overlay.dark;
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

				/*
				 * VisualLayer 위에 표시하되,
				 * TitleLayer와 CaptionLayer보다 아래에 둡니다.
				 */
				zIndex: 15,
			}}
		/>
	);
};