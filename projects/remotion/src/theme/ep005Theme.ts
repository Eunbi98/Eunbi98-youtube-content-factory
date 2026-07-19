import {SAFE_FRAME} from '../layout/SafeFrame';

export const ep005Theme = {
	backgroundColor: '#17212D',

	titleColor: '#7BFEB4',
	captionColor: '#FFFFFF',
	accentColor: '#7BFEB4',

	fontFamily:
		'"Pretendard", "Noto Sans KR", "Noto Sans CJK KR", "Apple SD Gothic Neo", Arial, sans-serif',

	title: {
		top: SAFE_FRAME.title.top,
		left: SAFE_FRAME.title.left,
		right: SAFE_FRAME.title.right,
		height: SAFE_FRAME.title.height,

		fontSize: 112,
		fontWeight: 950,
		lineHeight: 1.02,

		letterSpacing: '-0.065em',
		textAlign: 'center' as const,

		color: '#7BFEB4',

		textStroke: '6px #07110C',

		textShadow: [
			'0 4px 0 rgba(0, 0, 0, 0.95)',
			'0 8px 16px rgba(0, 0, 0, 0.90)',
			'0 0 6px rgba(0, 0, 0, 1)',
		].join(', '),
	},

	visual: {
		top: SAFE_FRAME.video.top,
		bottom: SAFE_FRAME.video.bottom,
		left: SAFE_FRAME.video.left,
		right: SAFE_FRAME.video.right,
	},

	caption: {
		left: SAFE_FRAME.caption.left,
		right: SAFE_FRAME.caption.right,
		bottom: SAFE_FRAME.caption.bottom,

		width: '100%',
		maxLines: 2,

		fontSize: 58,
		fontWeight: 800,
		lineHeight: 1.2,

		letterSpacing: '-0.035em',
		textAlign: 'center' as const,

		color: '#FFFFFF',

		textStroke: '2.5px #000000',

		textShadow: [
			'0 3px 2px rgba(0, 0, 0, 0.95)',
			'0 6px 12px rgba(0, 0, 0, 1)',
		].join(', '),
	},

	overlay: {
		/*
		 * 제목 뒤쪽을 어둡게 하되,
		 * 화면 중앙부는 원본 영상의 밝기를 유지합니다.
		 */
		cinematic: [
			'linear-gradient(',
			'180deg,',
			'rgba(0, 0, 0, 0.58) 0%,',
			'rgba(0, 0, 0, 0.34) 16%,',
			'rgba(0, 0, 0, 0.08) 34%,',
			'rgba(0, 0, 0, 0.02) 56%,',
			'rgba(0, 0, 0, 0.18) 72%,',
			'rgba(0, 0, 0, 0.72) 100%',
			')',
		].join(' '),

		/*
		 * 가장자리만 약하게 어둡게 만들어
		 * 시선이 영상 중앙으로 모이게 합니다.
		 */
		vignette: [
			'radial-gradient(',
			'ellipse at center,',
			'rgba(0, 0, 0, 0) 42%,',
			'rgba(0, 0, 0, 0.10) 66%,',
			'rgba(0, 0, 0, 0.48) 100%',
			')',
		].join(' '),

		dark: 'rgba(0, 0, 0, 0.42)',
	},
} as const;
