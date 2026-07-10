import React from 'react';
import {
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import {ep005Theme} from '../theme/ep005Theme';

type CaptionLayerProps = {
	caption?: string;
	color?: string;
};

export const CaptionLayer: React.FC<
	CaptionLayerProps
> = ({caption, color}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();

	if (!caption) {
		return null;
	}

	const entrance = spring({
		frame,
		fps,
		config: {
			damping: 18,
			stiffness: 150,
			mass: 0.7,
		},
	});

	const translateY =
		(1 - entrance) * 18;

	return (
		<div
			style={{
				position: 'absolute',

				left: ep005Theme.caption.left,
				right: ep005Theme.caption.right,
				bottom: ep005Theme.caption.bottom,

				display: 'flex',
				justifyContent: 'center',
				alignItems: 'center',

				opacity: entrance,

				transform:
					`translateY(${translateY}px)`,

				zIndex: 20,
			}}
		>
			<div
				style={{
					fontFamily:
						ep005Theme.fontFamily,

					fontSize:
						ep005Theme.caption.fontSize,

					fontWeight:
						ep005Theme.caption.fontWeight,

					lineHeight:
						ep005Theme.caption.lineHeight,

					letterSpacing:
						ep005Theme.caption.letterSpacing,

					textAlign:
						ep005Theme.caption.textAlign,

					color:
						color ??
						ep005Theme.caption.color,

					WebkitTextStroke:
						ep005Theme.caption.textStroke,

					textShadow:
						ep005Theme.caption.textShadow,

					whiteSpace: 'pre-wrap',
					wordBreak: 'keep-all',
				}}
			>
				{caption}
			</div>
		</div>
	);
};