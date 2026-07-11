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

import type {
	WordTiming,
} from '../types/timeline';


type CaptionLayerProps = {
	caption?: string;
	color?: string;
	durationInFrames?: number;
	wordTimings?: WordTiming[];
};


type CaptionPageTiming = {
	index: number;
	startFrame: number;
	endFrame: number;
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


const normalizeWord = (
	text: string,
): string => {
	return text
		.toLowerCase()
		.replace(
			/[\s,.!?，。！？"'“”‘’()[\]{}:;·…\-_/\\]/g,
			'',
		)
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
		.map(
			(part) =>
				part.trim(),
		)
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
		text
			.split(/\s+/)
			.filter(Boolean);

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
		pages.push(
			currentPage,
		);
	}

	return pages;
};


const rebalanceLastPage = (
	inputPages: string[],
): string[] => {
	const pages = [
		...inputPages,
	];

	if (pages.length < 2) {
		return pages;
	}

	const lastIndex =
		pages.length - 1;

	const lastPage =
		pages[lastIndex];

	const lastPageIsTooShort =
		getVisibleLength(
			lastPage,
		) <
			MIN_LAST_PAGE_LENGTH ||
		getWordCount(
			lastPage,
		) <
			MIN_LAST_PAGE_WORDS;

	if (!lastPageIsTooShort) {
		return pages;
	}

	const previousPage =
		pages[
			lastIndex - 1
		];

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
			getVisibleLength(
				normalized,
			) < 6 &&
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

		result.push(
			normalized,
		);
	}

	return result;
};


const buildCaptionPages = (
	text: string,
): string[] => {
	const normalized =
		normalizeCaption(
			text,
		);

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
			text.slice(
				0,
				middle,
			),
			text.slice(
				middle,
			),
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
				.slice(
					0,
					index,
				)
				.join(' ');

		const secondLine =
			words
				.slice(
					index,
				)
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
			.slice(
				0,
				bestIndex,
			)
			.join(' '),

		words
			.slice(
				bestIndex,
			)
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


const buildFallbackPageTimings = (
	{
		pages,
		durationInFrames,
	}: {
		pages: string[];
		durationInFrames: number;
	},
): CaptionPageTiming[] => {
	if (pages.length === 0) {
		return [];
	}

	const safeDuration =
		Math.max(
			pages.length,
			durationInFrames,
		);

	const weights =
		getPageWeights(
			pages,
		);

	const totalWeight =
		weights.reduce(
			(sum, value) =>
				sum + value,
			0,
		);

	const timings: CaptionPageTiming[] = [];

	let accumulatedFrame = 0;

	for (
		let index = 0;
		index < pages.length;
		index += 1
	) {
		const isLast =
			index ===
			pages.length - 1;

		const remainingPages =
			pages.length -
			index -
			1;

		const remainingFrames =
			safeDuration -
			accumulatedFrame;

		const calculatedDuration =
			Math.max(
				1,
				Math.round(
					safeDuration *
						(
							weights[index] /
							totalWeight
						),
				),
			);

		const pageDuration =
			isLast
				? remainingFrames
				: Math.max(
						1,
						Math.min(
							calculatedDuration,
							remainingFrames -
								remainingPages,
						),
					);

		const endFrame =
			isLast
				? safeDuration
				: accumulatedFrame +
					pageDuration;

		timings.push({
			index,
			startFrame:
				accumulatedFrame,
			endFrame,
		});

		accumulatedFrame =
			endFrame;
	}

	return timings;
};


const getPageWords = (
	page: string,
): string[] => {
	return page
		.split(/\s+/)
		.map(
			(word) =>
				normalizeWord(
					word,
				),
		)
		.filter(Boolean);
};


const getTimingWords = (
	wordTimings: WordTiming[],
): Array<{
	timing: WordTiming;
	normalizedText: string;
}> => {
	return wordTimings
		.filter(
			(timing) =>
				Number.isFinite(
					timing.offset,
				) &&
				Number.isFinite(
					timing.end,
				) &&
				timing.offset >= 0 &&
				timing.end >=
					timing.offset,
		)
		.map(
			(timing) => ({
				timing,
				normalizedText:
					normalizeWord(
						timing.text,
					),
			}),
		)
		.filter(
			(item) =>
				Boolean(
					item.normalizedText,
				),
		);
};


const wordsAreCompatible = (
	pageWord: string,
	timingWord: string,
): boolean => {
	if (
		pageWord === timingWord
	) {
		return true;
	}

	if (
		pageWord.includes(
			timingWord,
		) ||
		timingWord.includes(
			pageWord,
		)
	) {
		return true;
	}

	return false;
};


const findPageWordRange = (
	{
		pageWords,
		timingWords,
		searchStartIndex,
	}: {
		pageWords: string[];
		timingWords: Array<{
			timing: WordTiming;
			normalizedText: string;
		}>;
		searchStartIndex: number;
	},
): {
	startIndex: number;
	endIndex: number;
} | null => {
	if (
		pageWords.length === 0 ||
		searchStartIndex >=
			timingWords.length
	) {
		return null;
	}

	let timingIndex =
		searchStartIndex;

	let pageWordIndex = 0;

	let matchedStartIndex = -1;

	while (
		timingIndex <
			timingWords.length &&
		pageWordIndex <
			pageWords.length
	) {
		const pageWord =
			pageWords[
				pageWordIndex
			];

		const timingWord =
			timingWords[
				timingIndex
			].normalizedText;

		if (
			wordsAreCompatible(
				pageWord,
				timingWord,
			)
		) {
			if (
				matchedStartIndex < 0
			) {
				matchedStartIndex =
					timingIndex;
			}

			pageWordIndex += 1;
			timingIndex += 1;

			continue;
		}

		if (
			matchedStartIndex < 0
		) {
			timingIndex += 1;
			continue;
		}

		/*
		 * Edge TTS가 조사 또는 숫자를 별도 토큰으로
		 * 나누는 경우를 허용합니다.
		 */
		const nextTimingWord =
			timingWords[
				timingIndex + 1
			]?.normalizedText;

		if (
			nextTimingWord &&
			wordsAreCompatible(
				pageWord,
				`${timingWord}${nextTimingWord}`,
			)
		) {
			pageWordIndex += 1;
			timingIndex += 2;

			continue;
		}

		break;
	}

	if (
		matchedStartIndex < 0 ||
		pageWordIndex <
			pageWords.length
	) {
		return null;
	}

	return {
		startIndex:
			matchedStartIndex,

		endIndex:
			Math.max(
				matchedStartIndex,
				timingIndex - 1,
			),
	};
};


const buildWordTimingPageTimings = (
	{
		pages,
		wordTimings,
		fps,
		durationInFrames,
	}: {
		pages: string[];
		wordTimings: WordTiming[];
		fps: number;
		durationInFrames: number;
	},
): CaptionPageTiming[] | null => {
	if (
		pages.length === 0 ||
		wordTimings.length === 0
	) {
		return null;
	}

	const timingWords =
		getTimingWords(
			wordTimings,
		);

	if (timingWords.length === 0) {
		return null;
	}

	const ranges: Array<{
		startIndex: number;
		endIndex: number;
	}> = [];

	let searchStartIndex = 0;

	for (const page of pages) {
		const pageWords =
			getPageWords(
				page,
			);

		const range =
			findPageWordRange({
				pageWords,
				timingWords,
				searchStartIndex,
			});

		if (!range) {
			return null;
		}

		ranges.push(
			range,
		);

		searchStartIndex =
			range.endIndex + 1;
	}

	const pageTimings =
		ranges.map(
			(range, index) => {
				const firstWord =
					timingWords[
						range.startIndex
					].timing;

				const isLastPage =
					index ===
					ranges.length - 1;

				const nextRange =
					ranges[
						index + 1
					];

				const rawStartFrame =
					Math.floor(
						firstWord.offset *
							fps,
					);

				const rawEndFrame =
					isLastPage
						? durationInFrames
						: Math.floor(
								timingWords[
									nextRange
										.startIndex
								].timing
									.offset *
									fps,
							);

				const startFrame =
					Math.max(
						0,
						Math.min(
							durationInFrames -
								1,
							rawStartFrame,
						),
					);

				const endFrame =
					Math.max(
						startFrame + 1,
						Math.min(
							durationInFrames,
							rawEndFrame,
						),
					);

				return {
					index,
					startFrame,
					endFrame,
				};
			},
		);

	/*
	 * 첫 단어 전의 짧은 무음 구간에도
	 * 첫 자막이 보이도록 시작 프레임을 0으로 고정합니다.
	 */
	if (pageTimings.length > 0) {
		pageTimings[0] = {
			...pageTimings[0],
			startFrame: 0,
		};
	}

	return pageTimings;
};


const getActivePage = (
	{
		frame,
		pageTimings,
	}: {
		frame: number;
		pageTimings: CaptionPageTiming[];
	},
): CaptionPageTiming => {
	const found =
		pageTimings.find(
			(page) =>
				frame >=
					page.startFrame &&
				frame <
					page.endFrame,
		);

	if (found) {
		return found;
	}

	if (
		frame <
		pageTimings[0].startFrame
	) {
		return pageTimings[0];
	}

	return pageTimings[
		pageTimings.length - 1
	];
};


export const CaptionLayer:
React.FC<
	CaptionLayerProps
> = ({
	caption,
	color,
	durationInFrames,
	wordTimings,
}) => {
	const frame =
		useCurrentFrame();

	const {
		fps,
		durationInFrames:
			compositionDurationInFrames,
	} = useVideoConfig();

	const resolvedDuration =
		Math.max(
			1,
			Math.floor(
				durationInFrames ??
					compositionDurationInFrames,
			),
		);

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

	const pageTimings =
		useMemo(
			() => {
				if (
					pages.length === 0
				) {
					return [];
				}

				const wordTimingResult =
					wordTimings &&
					wordTimings.length > 0
						? buildWordTimingPageTimings({
								pages,
								wordTimings,
								fps,
								durationInFrames:
									resolvedDuration,
							})
						: null;

				if (wordTimingResult) {
					return wordTimingResult;
				}

				return buildFallbackPageTimings({
					pages,
					durationInFrames:
						resolvedDuration,
				});
			},
			[
				pages,
				wordTimings,
				fps,
				resolvedDuration,
			],
		);

	if (
		!caption ||
		pages.length === 0 ||
		pageTimings.length === 0
	) {
		return null;
	}

	const activePage =
		getActivePage({
			frame,
			pageTimings,
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