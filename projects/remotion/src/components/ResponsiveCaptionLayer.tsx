import React, {useMemo} from 'react';
import {
	interpolate,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import type {WordTiming} from '../types/timeline';
import {CaptionLayer} from './CaptionLayer';


type Props = {
	caption?: string;
	color?: string;
	durationInFrames?: number;
	wordTimings?: WordTiming[];
};

const normalize = (text: string): string =>
	text.replace(/\r/g, ' ').replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();

const splitLongformCaption = (text: string): string[] => {
	const normalized = normalize(text);
	if (!normalized) return [];

	const sentenceParts = normalized.match(/(?:\d+\.\d+|[^.!?。！？])+[.!?。！？]?/g) ?? [normalized];
	const pages: string[] = [];
	const maxLength = 72;

	for (const sentence of sentenceParts.map((part) => part.trim()).filter(Boolean)) {
		if (sentence.length <= maxLength) {
			pages.push(sentence);
			continue;
		}

		const words = sentence.split(/\s+/).filter(Boolean);
		if (words.length <= 1) {
			for (let i = 0; i < sentence.length; i += maxLength) {
				pages.push(sentence.slice(i, i + maxLength));
			}
			continue;
		}

		let current = '';
		for (const word of words) {
			const candidate = current ? `${current} ${word}` : word;
			if (candidate.length <= maxLength) {
				current = candidate;
			} else {
				if (current) pages.push(current);
				current = word;
			}
		}
		if (current) pages.push(current);
	}

	return pages;
};

export const ResponsiveCaptionLayer: React.FC<Props> = ({
	caption,
	color,
	durationInFrames = 1,
	wordTimings,
}) => {
	const frame = useCurrentFrame();
	const {width, height} = useVideoConfig();
	const isLandscape = width > height;
	const pages = useMemo(
		() => splitLongformCaption(caption ?? ''),
		[caption],
	);

	if (!isLandscape) {
		return (
			<CaptionLayer
				caption={caption}
				color={color}
				durationInFrames={durationInFrames}
				wordTimings={wordTimings}
			/>
		);
	}

	if (pages.length === 0) return null;

	const progress = Math.min(
		0.999999,
		Math.max(0, frame / Math.max(1, durationInFrames)),
	);
	const pageIndex = Math.min(
		pages.length - 1,
		Math.floor(progress * pages.length),
	);
	const localProgress = progress * pages.length - pageIndex;
	const opacity = interpolate(
		localProgress,
		[0, 0.05, 0.92, 1],
		[0, 1, 1, 0],
		{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
	);

	return (
		<div
			style={{
				position: 'absolute',
				left: 110,
				right: 110,
				bottom: 58,
				display: 'flex',
				justifyContent: 'center',
				zIndex: 40,
				pointerEvents: 'none',
				opacity,
			}}
		>
			<div
				style={{
					maxWidth: 1540,
					padding: '14px 28px 16px',
					borderRadius: 14,
					backgroundColor: 'rgba(0, 0, 0, 0.58)',
					fontFamily: '"Pretendard", "Noto Sans KR", "Noto Sans CJK KR", Arial, sans-serif',
					fontSize: 44,
					fontWeight: 760,
					lineHeight: 1.32,
					letterSpacing: '-0.025em',
					textAlign: 'center',
					color: color ?? '#FFFFFF',
					textShadow: '0 2px 6px rgba(0,0,0,0.9)',
					wordBreak: 'keep-all',
				}}
			>
				{pages[pageIndex]}
			</div>
		</div>
	);
};
