import React, {
	useMemo,
} from 'react';

import {
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import {
	ep005Theme,
} from '../theme/ep005Theme';


type CaptionLayerProps = {
	caption?: string;
	color?: string;
	durationInFrames?: number;
};


const MAX_PAGE_LENGTH = 34;
const MAX_LINE_LENGTH = 18;

const MIN_LAST_PAGE_LENGTH = 8;
const MIN_LAST_PAGE_WORDS = 2;


const normalizeCaption = (
	text: string,
): string => {
	return text
		.replace(/\r/g, ' ')
		.replace(/\n/g, ' ')
		.replace(/\s+/g, ' ')
		.trim();
};


const getVisibleLength = (
	text: string,
): number => {
	return text
		.replace(/\s/g, '')
		.length;
};


const getWordCount = (
	text: string,
): number => {
	return text
		.trim()
		.split(/\s+/)
		.filter(Boolean)
		.length;
};


const splitBySentence = (
	text: string,
): string[] => {
	const matches =
		text.match(
			/[^.!?。！？]+[.!?。！？]?/g,
		);

	if (!matches) {
		return [text];
	}

	return matches
		.map((part) => part.trim())
		.filter(Boolean);
};


const splitLongSentence = (
	text: string,
): string[] => {
	if (
		text.length <=
		MAX_PAGE_LENGTH
	) {
		return [text];
	}

	const words =
		text.split(/\s+/);

	const pages: string[] = [];
	let currentPage = '';

	for (const word of words) {
		const candidate =
			currentPage
				? `${currentPage} ${word}`
				: word;

		if (
			candidate.length <=
			MAX_PAGE_LENGTH
		) {
			currentPage = candidate;
			continue;
		}

		if (currentPage) {
			pages.push(
				currentPage,
			);
		}

		currentPage = word;
	}

	if (currentPage) {
		pages.push(currentPage);
	}

	return pages;
};


/**
 * 마지막 페이지에 단어 하나만 남거나 너무 짧으면
 * 이전 페이지의 뒷부분을 함께 이동시킵니다.
 *
 * 예:
 *   최고의 시절이자 최악의 시절,
 *   지혜의 시대이자 어리석음의 시대였습니다.
 *
 * 잘못된 분할:
 *   지혜의 시대이자 어리석음의
 *   시대였습니다.
 *
 * 보정:
 *   지혜의 시대이자
 *   어리석음의 시대였습니다.
 */
const rebalanceLastPage = (
	inputPages: string[],
): string[] => {
	const pages = [...inputPages];

	if (pages.length < 2) {
		return pages;
	}

	const lastIndex =
		pages.length - 1;

	const lastPage =
		pages[lastIndex];

	const lastPageIsTooShort =
		getVisibleLength(lastPage) <
			MIN_LAST_PAGE_LENGTH ||
		getWordCount(lastPage) <
			MIN_LAST_PAGE_WORDS;

	if (!lastPageIsTooShort) {
		return pages;
	}

	const previousPage =
		pages[lastIndex - 1];

	const previousWords =
		previousPage
			.split(/\s+/)
			.filter(Boolean);

	const lastWords =
		lastPage
			.split(/\s+/)
			.filter(Boolean);

	while (
		previousWords.length > 2 &&
		(
			lastWords.length <
				MIN_LAST_PAGE_WORDS ||
			getVisibleLength(
				lastWords.join(' '),
			) <
				MIN_LAST_PAGE_LENGTH
		)
	) {
		const movedWord =
			previousWords.pop();

		if (!movedWord) {
			break;
		}

		lastWords.unshift(
			movedWord,
		);
	}

	const resolvedPrevious =
		previousWords.join(' ');

	const resolvedLast =
		lastWords.join(' ');

	if (
		resolvedPrevious &&
		resolvedLast
	) {
		pages[lastIndex - 1] =
			resolvedPrevious;

		pages[lastIndex] =
			resolvedLast;
	}

	return pages;
};


const mergeVeryShortPages = (
	inputPages: string[],
): string[] => {
	const result: string[] = [];

	for (const page of inputPages) {
		const normalized =
			page.trim();

		if (!normalized) {
			continue;
		}

		const previous =
			result[
				result.length - 1
			];

		if (
			previous &&
			getVisibleLength(normalized) <
				6 &&
			`${previous} ${normalized}`
				.length <=
				MAX_PAGE_LENGTH
		) {
			result[
				result.length - 1
			] =
				`${previous} ${normalized}`;

			continue;
		}

		result.push(normalized);
	}

	return result;
};


const buildCaptionPages = (
	text: string,
): string[] => {
	const normalized =
		normalizeCaption(text);

	if (!normalized) {
		return [];
	}

	const sentenceParts =
		splitBySentence(
			normalized,
		);

	const pages =
		sentenceParts.flatMap(
			(sentence) =>
				splitLongSentence(
					sentence,
				),
		);

	const merged =
		mergeVeryShortPages(
			pages,
		);

	return rebalanceLastPage(
		merged,
	);
};


const addBalancedLineBreak = (
	text: string,
): string => {
	if (
		text.length <=
		MAX_LINE_LENGTH
	) {
		return text;
	}

	const words =
		text
			.split(/\s+/)
			.filter(Boolean);

	if (words.length <= 1) {
		const middle =
			Math.ceil(
				text.length / 2,
			);

		return [
			text.slice(0, middle),
			text.slice(middle),
		].join('\n');
	}

	let bestIndex = 1;
	let bestScore =
		Number.POSITIVE_INFINITY;

	for (
		let index = 1;
		index < words.length;
		index += 1
	) {
		const firstLine =
			words
				.slice(0, index)
				.join(' ');

		const secondLine =
			words
				.slice(index)
				.join(' ');

		const lengthDifference =
			Math.abs(
				firstLine.length -
					secondLine.length,
			);

		const overflowPenalty =
			Math.max(
				0,
				firstLine.length -
					MAX_LINE_LENGTH,
			) *
				100 +
			Math.max(
				0,
				secondLine.length -
					MAX_LINE_LENGTH,
			) *
				100;

		const orphanPenalty =
			getWordCount(
				secondLine,
			) < 2
				? 500
				: 0;

		const score =
			lengthDifference +
			overflowPenalty +
			orphanPenalty;

		if (score < bestScore) {
			bestScore = score;
			bestIndex = index;
		}
	}

	return [
		words
			.slice(0, bestIndex)
			.join(' '),

		words
			.slice(bestIndex)
			.join(' '),
	].join('\n');
};


const getPageWeights = (
	pages: string[],
): number[] => {
	return pages.map(
		(page) =>
			Math.max(
				6,
				getVisibleLength(
					page,
				),
			),
	);
};


const getActivePageIndex = (
	{
		frame,
		pages,
		durationInFrames,
	}: {
		frame: number;
		pages: string[];
		durationInFrames: number;
	},
): {
	index: number;
	startFrame: number;
} => {
	if (pages.length <= 1) {
		return {
			index: 0,
			startFrame: 0,
		};
	}

	const weights =
		getPageWeights(pages);

	const totalWeight =
		weights.reduce(
			(sum, value) =>
				sum + value,
			0,
		);

	let accumulatedFrame = 0;

	for (
		let index = 0;
		index < pages.length;
		index += 1
	) {
		const isLast =
			index ===
			pages.length - 1;

		const pageDuration =
			isLast
				? durationInFrames -
					accumulatedFrame
				: Math.max(
						1,
						Math.round(
							durationInFrames *
								(
									weights[index] /
									totalWeight
								),
						),
					);

		const endFrame =
			isLast
				? durationInFrames
				: accumulatedFrame +
					pageDuration;

		if (
			frame >= accumulatedFrame &&
			frame < endFrame
		) {
			return {
				index,
				startFrame:
					accumulatedFrame,
			};
		}

		accumulatedFrame =
			endFrame;
	}

	return {
		index:
			pages.length - 1,

		startFrame:
			Math.max(
				0,
				accumulatedFrame - 1,
			),
	};
};


export const CaptionLayer:
React.FC<
	CaptionLayerProps
> = ({
	caption,
	color,
	durationInFrames,
}) => {
	const frame =
		useCurrentFrame();

	const {
		fps,
		durationInFrames:
			compositionDurationInFrames,
	} = useVideoConfig();

	const pages = useMemo(
		() => {
			if (!caption) {
				return [];
			}

			return buildCaptionPages(
				caption,
			);
		},
		[caption],
	);

	if (
		!caption ||
		pages.length === 0
	) {
		return null;
	}

	const resolvedDuration =
		Math.max(
			1,
			Math.floor(
				durationInFrames ??
					compositionDurationInFrames,
			),
		);

	const activePage =
		getActivePageIndex({
			frame,
			pages,
			durationInFrames:
				resolvedDuration,
		});

	const localFrame =
		Math.max(
			0,
			frame -
				activePage.startFrame,
		);

	const entrance =
		spring({
			frame:
				localFrame,

			fps,

			config: {
				damping: 18,
				stiffness: 150,
				mass: 0.7,
			},
		});

	const translateY =
		(1 - entrance) * 18;

	const displayedCaption =
		addBalancedLineBreak(
			pages[
				activePage.index
			],
		);

	return (
		<div
			style={{
				position:
					'absolute',

				left:
					ep005Theme
						.caption
						.left,

				right:
					ep005Theme
						.caption
						.right,

				bottom:
					ep005Theme
						.caption
						.bottom,

				display:
					'flex',

				alignItems:
					'center',

				justifyContent:
					'center',

				textAlign:
					ep005Theme
						.caption
						.textAlign,

				fontFamily:
					ep005Theme
						.fontFamily,

				fontSize:
					ep005Theme
						.caption
						.fontSize,

				fontWeight:
					ep005Theme
						.caption
						.fontWeight,

				lineHeight:
					ep005Theme
						.caption
						.lineHeight,

				letterSpacing:
					ep005Theme
						.caption
						.letterSpacing,

				color:
					color ??
					ep005Theme
						.caption
						.color,

				WebkitTextStroke:
					ep005Theme
						.caption
						.textStroke,

				textShadow:
					ep005Theme
						.caption
						.textShadow,

				whiteSpace:
					'pre-line',

				wordBreak:
					'keep-all',

				overflowWrap:
					'break-word',

				overflow:
					'visible',

				opacity:
					entrance,

				transform:
					`translateY(${translateY}px)`,

				zIndex:
					30,
			}}
		>
			{displayedCaption}
		</div>
	);
};