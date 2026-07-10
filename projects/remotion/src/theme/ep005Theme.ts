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
		/*
		 * 제목을 검은 상단 영역이 아니라
		 * 영상 위쪽에 겹쳐 표시합니다.
		 */
		top: SAFE_FRAME.video.top + 30,
		left: 55,
		right: 55,
		height: 250,

		/*
		 * 기존 70px보다 크게 설정합니다.
		 */
		fontSize: 104,
		fontWeight: 900,
		lineHeight: 1.06,

		letterSpacing: '-0.055em',
		textAlign: 'center' as const,

		color: '#63E88F',

		/*
		 * EP005 스타일의 검은 외곽선과 그림자.
		 */
		textStroke: '4px #07110C',

		textShadow: [
			'0 4px 0 rgba(0, 0, 0, 0.95)',
			'0 8px 14px rgba(0, 0, 0, 0.90)',
			'0 0 5px rgba(0, 0, 0, 1)',
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