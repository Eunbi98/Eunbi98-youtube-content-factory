import {SAFE_FRAME} from '../layout/SafeFrame';

export const ep005Theme = {
	backgroundColor: '#17212D',

	titleColor: '#7cffb2',
	captionColor: '#FFFFFF',
	accentColor: '#7cffb2',

	fontFamily:
		'"Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif',

	title: {
		top: SAFE_FRAME.title.top,
		left: SAFE_FRAME.title.left,
		right: SAFE_FRAME.title.right,
		height: SAFE_FRAME.title.height,

		fontSize: 112,
		fontWeight: 900,
		lineHeight: 1.02,

		letterSpacing: '-0.065em',
		textAlign: 'center' as const,

		color: '#7cffb2',

		textStroke: '5px #07110C',

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
} as const;