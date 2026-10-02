import React from 'react';
import {
	interpolate,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import {TitleLayer} from './TitleLayer';


type Props = {
	title: string;
	color?: string;
};

export const ResponsiveTitleLayer: React.FC<Props> = ({title, color}) => {
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const isLandscape = width > height;

	if (!isLandscape) {
		return <TitleLayer title={title} color={color} />;
	}

	const opacity = interpolate(
		frame,
		[0, Math.round(fps * 0.4), Math.round(fps * 4.2), Math.round(fps * 5.0)],
		[0, 1, 1, 0],
		{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
	);

	return (
		<div
			style={{
				position: 'absolute',
				top: 46,
				left: 64,
				maxWidth: 1280,
				padding: '10px 18px 12px',
				borderRadius: 12,
				backgroundColor: 'rgba(0,0,0,0.42)',
				fontFamily: '"Pretendard", "Noto Sans KR", "Noto Sans CJK KR", Arial, sans-serif',
				fontSize: 42,
				fontWeight: 800,
				lineHeight: 1.2,
				letterSpacing: '-0.03em',
				color: color ?? '#FFFFFF',
				textShadow: '0 2px 8px rgba(0,0,0,0.9)',
				opacity,
				zIndex: 45,
				pointerEvents: 'none',
				wordBreak: 'keep-all',
			}}
		>
			{title}
		</div>
	);
};
