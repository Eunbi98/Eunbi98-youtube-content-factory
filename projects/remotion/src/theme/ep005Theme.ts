import {SAFE_FRAME} from '../layout/SafeFrame';

export const ep005Theme = {
	backgroundColor: '#17212D',

	/*
	 * EP005 원본 제목에 가까운 민트 그린.
	 */
	titleColor: '#63E88F',

	captionColor: '#FFFFFF',
	accentColor: '#63E88F',

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

	letterSpacing: "-0.065em",

	textAlign: "center" as const,

	color: "#63E88F",

	textStroke: "5px #07110C",

	textShadow: [
		"0 4px 0 rgba(0,0,0,0.95)",
		"0 8px 16px rgba(0,0,0,0.90)",
		"0 0 6px rgba(0,0,0,1)",
	].join(", "),
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

		textShadow: [
			'0 3px 2px rgba(0, 0, 0, 0.95)',
			'0 6px 12px rgba(0, 0, 0, 1)',
		].join(', '),
	},
};