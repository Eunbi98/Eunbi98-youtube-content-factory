export const quizTheme = {
	fontFamily:
		'Pretendard, "Noto Sans KR", Arial, sans-serif',

	colors: {
		background: '#6FB382',
		backgroundDark: '#5A9D70',
		paper: '#F8F6EE',
		paperShadow: '#4E855E',
		ink: '#214F2A',
		inkSoft: '#3E6845',
		accent: '#F6D25B',
		accentSoft: '#FBE69A',
		answer: '#6DBB82',
		white: '#FFFFFF',
	},

	safeArea: {
		top: 150,
		right: 70,
		bottom: 190,
		left: 70,
	},

	header: {
		top: 150,
		height: 130,
		fontSize: 54,
		fontWeight: 800,
	},

	card: {
		top: 315,
		right: 70,
		bottom: 300,
		left: 70,
		borderWidth: 9,
		borderRadius: 50,
		paddingHorizontal: 70,
		paddingVertical: 85,
		shadowOffset: 18,
	},

	label: {
		height: 86,
		paddingHorizontal: 36,
		fontSize: 40,
		fontWeight: 800,
		borderRadius: 43,
	},

	question: {
		fontSize: 78,
		fontWeight: 900,
		lineHeight: 1.28,
		letterSpacing: -2.8,
		maxWidth: 790,
	},

	countdown: {
		fontSize: 330,
		fontWeight: 900,
		strokeWidth: 16,
	},

	answer: {
		labelFontSize: 48,
		answerFontSize: 130,
		fontWeight: 900,
		lineHeight: 1.12,
		letterSpacing: -4,
	},

	footer: {
		bottom: 205,
		fontSize: 38,
		fontWeight: 700,
	},

	intro: {
		titleFontSize: 104,
		subtitleFontSize: 46,
	},

	ending: {
		titleFontSize: 82,
		subtitleFontSize: 40,
	},
} as const;