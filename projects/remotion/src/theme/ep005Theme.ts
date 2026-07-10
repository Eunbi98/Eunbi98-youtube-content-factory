import {SAFE_FRAME} from '../layout/SafeFrame';

export const ep005Theme = {
	backgroundColor: '#000000',

	titleColor: '#F4D35E',
	captionColor: '#FFFFFF',
	accentColor: '#F4D35E',

	fontFamily:
		'"Pretendard", "Noto Sans KR", "Apple SD Gothic Neo", Arial, sans-serif',

	title: {
		top: SAFE_FRAME.title.top,
		left: SAFE_FRAME.title.left,
		right: SAFE_FRAME.title.right,
		height: SAFE_FRAME.title.height,

		fontSize: 70,
		fontWeight: 900,
		lineHeight: 1.08,

		letterSpacing: '-0.045em',
		textAlign: 'center' as const,

		textShadow:
			'0 4px 10px rgba(0, 0, 0, 0.95)',
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

		fontSize: 58,
		fontWeight: 800,
		lineHeight: 1.2,

		letterSpacing: '-0.035em',
		textAlign: 'center' as const,

		color: '#FFFFFF',

		textStroke: '2.5px #000000',

		textShadow:
			'0 4px 12px rgba(0, 0, 0, 1)',
	},
};