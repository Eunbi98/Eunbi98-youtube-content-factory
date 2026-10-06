import React from 'react';

import {
	AbsoluteFill,
	interpolate,
	spring,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import type {
	TimelineScene,
} from '../types/timeline';

import {
	quizTheme,
} from './quizTheme';

type QuizSceneRendererProps = {
	scene: TimelineScene;
	episodeTitle: string;
};

const PaperCard: React.FC<{
	children: React.ReactNode;
}> = ({children}) => {
	const theme = quizTheme;

	return (
		<div
			style={{
				position: 'absolute',

				top: theme.card.top,
				left: theme.card.left,
				right: theme.card.right,
				bottom: theme.card.bottom,

				padding: `${theme.card.paddingVertical}px ${theme.card.paddingHorizontal}px`,

				display: 'flex',
				flexDirection: 'column',
				alignItems: 'center',
				justifyContent: 'center',

				backgroundColor:
					theme.colors.paper,

				border:
					`${theme.card.borderWidth}px solid ${theme.colors.ink}`,

				borderRadius:
					theme.card.borderRadius,

				boxShadow:
					`${theme.card.shadowOffset}px ${theme.card.shadowOffset}px 0 ${theme.colors.paperShadow}`,

				overflow: 'hidden',
			}}
		>
			{children}
		</div>
	);
};

const Header: React.FC<{
	text: string;
}> = ({text}) => {
	const theme = quizTheme;

	return (
		<div
			style={{
				position: 'absolute',

				top: theme.header.top,
				left: theme.safeArea.left,
				right: theme.safeArea.right,
				height: theme.header.height,

				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',

				fontFamily:
					theme.fontFamily,

				fontSize:
					theme.header.fontSize,

				fontWeight:
					theme.header.fontWeight,

				color:
					theme.colors.ink,

				letterSpacing: -1.5,
			}}
		>
			{text}
		</div>
	);
};

const Footer: React.FC<{
	text: string;
}> = ({text}) => {
	const theme = quizTheme;

	return (
		<div
			style={{
				position: 'absolute',

				left: theme.safeArea.left,
				right: theme.safeArea.right,
				bottom: theme.footer.bottom,

				textAlign: 'center',

				fontFamily:
					theme.fontFamily,

				fontSize:
					theme.footer.fontSize,

				fontWeight:
					theme.footer.fontWeight,

				color:
					theme.colors.inkSoft,
			}}
		>
			{text}
		</div>
	);
};

const IntroScene: React.FC<{
	scene: TimelineScene;
	episodeTitle: string;
}> = ({
	scene,
	episodeTitle,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const theme = quizTheme;

	const scale = spring({
		frame,
		fps,
		config: {
			damping: 14,
			stiffness: 130,
			mass: 0.8,
		},
	});

	const opacity = interpolate(
		frame,
		[0, 10],
		[0, 1],
		{
			extrapolateLeft: 'clamp',
			extrapolateRight: 'clamp',
		},
	);

	return (
		<AbsoluteFill
			style={{
				backgroundColor:
					theme.colors.background,

				fontFamily:
					theme.fontFamily,

				color:
					theme.colors.ink,
			}}
		>
			<PaperCard>
				<div
					style={{
						opacity,
						transform:
							`scale(${scale})`,

						textAlign: 'center',
					}}
				>
					<div
						style={{
							marginBottom: 38,

							fontSize:
								theme.intro.subtitleFontSize,

							fontWeight: 800,

							color:
								theme.colors.inkSoft,
						}}
					>
						오늘의 상식 퀴즈
					</div>

					<div
						style={{
							fontSize:
								theme.intro.titleFontSize,

							fontWeight: 900,

							lineHeight: 1.18,

							letterSpacing: -4,

							whiteSpace: 'pre-line',
						}}
					>
						{scene.caption ??
							episodeTitle}
					</div>

					<div
						style={{
							width: 260,
							height: 18,

							margin:
								'55px auto 0',

							borderRadius: 20,

							backgroundColor:
								theme.colors.accent,
						}}
					/>
				</div>
			</PaperCard>
		</AbsoluteFill>
	);
};

const QuestionScene: React.FC<{
	scene: TimelineScene;
}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const theme = quizTheme;

	const enter = spring({
		frame,
		fps,
		config: {
			damping: 16,
			stiffness: 120,
			mass: 0.8,
		},
	});

	const translateY = interpolate(
		enter,
		[0, 1],
		[45, 0],
	);

	const opacity = interpolate(
		enter,
		[0, 1],
		[0, 1],
	);

	return (
		<AbsoluteFill
			style={{
				backgroundColor:
					theme.colors.background,

				fontFamily:
					theme.fontFamily,

				color:
					theme.colors.ink,
			}}
		>
			<Header
				text={scene.title ?? '문제'}
			/>

			<PaperCard>
				<div
					style={{
						position: 'absolute',
						top: 70,

						height:
							theme.label.height,

						padding:
							`0 ${theme.label.paddingHorizontal}px`,

						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',

						borderRadius:
							theme.label.borderRadius,

						backgroundColor:
							theme.colors.accentSoft,

						fontSize:
							theme.label.fontSize,

						fontWeight:
							theme.label.fontWeight,

						color:
							theme.colors.ink,
					}}
				>
					주관식
				</div>

				<div
					style={{
						width: '100%',
						maxWidth:
							theme.question.maxWidth,

						opacity,

						transform:
							`translateY(${translateY}px)`,

						textAlign: 'center',

						fontSize:
							theme.question.fontSize,

						fontWeight:
							theme.question.fontWeight,

						lineHeight:
							theme.question.lineHeight,

						letterSpacing:
							theme.question.letterSpacing,

						wordBreak: 'keep-all',

						whiteSpace: 'pre-line',
					}}
				>
					{scene.caption}
				</div>
			</PaperCard>

			<Footer
				text="정답을 생각해보세요"
			/>
		</AbsoluteFill>
	);
};

const CountdownScene: React.FC<{
	scene: TimelineScene;
}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const theme = quizTheme;

	const scale = spring({
		frame,
		fps,
		config: {
			damping: 10,
			stiffness: 190,
			mass: 0.55,
		},
	});

	const value =
		scene.countdownValue ??
		Number(scene.caption) ??
		3;

	return (
		<AbsoluteFill
			style={{
				backgroundColor:
					theme.colors.background,

				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',

				fontFamily:
					theme.fontFamily,
			}}
		>
			<div
				style={{
					transform:
						`scale(${scale})`,

					fontSize:
						theme.countdown.fontSize,

					fontWeight:
						theme.countdown.fontWeight,

					lineHeight: 1,

					color:
						theme.colors.accent,

					WebkitTextStroke:
						`${theme.countdown.strokeWidth}px ${theme.colors.ink}`,

					textShadow:
						`14px 18px 0 ${theme.colors.paperShadow}`,
				}}
			>
				{value}
			</div>

			<div
				style={{
					position: 'absolute',

					left: 0,
					right: 0,
					bottom: 0,

					height: 250,

					backgroundColor:
						theme.colors.paper,

					borderTop:
						`9px solid ${theme.colors.ink}`,
				}}
			/>
		</AbsoluteFill>
	);
};

const AnswerScene: React.FC<{
	scene: TimelineScene;
}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const theme = quizTheme;

	const enter = spring({
		frame,
		fps,
		config: {
			damping: 12,
			stiffness: 150,
			mass: 0.65,
		},
	});

	const scale = interpolate(
		enter,
		[0, 1],
		[0.75, 1],
	);

	return (
		<AbsoluteFill
			style={{
				backgroundColor:
					theme.colors.background,

				fontFamily:
					theme.fontFamily,

				color:
					theme.colors.ink,
			}}
		>
			<Header text="정답 공개" />

			<PaperCard>
				<div
					style={{
						marginBottom: 55,

						fontSize:
							theme.answer.labelFontSize,

						fontWeight: 800,

						color:
							theme.colors.inkSoft,
					}}
				>
					정답은
				</div>

				<div
					style={{
						transform:
							`scale(${scale})`,

						padding:
							'42px 68px',

						borderRadius: 42,

						backgroundColor:
							theme.colors.answer,

						border:
							`8px solid ${theme.colors.ink}`,

						boxShadow:
							`12px 14px 0 ${theme.colors.accent}`,

						textAlign: 'center',

						fontSize:
							theme.answer.answerFontSize,

						fontWeight:
							theme.answer.fontWeight,

						lineHeight:
							theme.answer.lineHeight,

						letterSpacing:
							theme.answer.letterSpacing,

						wordBreak: 'keep-all',

						whiteSpace: 'pre-line',
					}}
				>
					{scene.caption}
				</div>
			</PaperCard>

			<Footer text="다음 문제도 도전해보세요" />
		</AbsoluteFill>
	);
};

const EndingScene: React.FC<{
	scene: TimelineScene;
}> = ({scene}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const theme = quizTheme;

	const scale = spring({
		frame,
		fps,
		config: {
			damping: 14,
			stiffness: 125,
			mass: 0.8,
		},
	});

	return (
		<AbsoluteFill
			style={{
				backgroundColor:
					theme.colors.background,

				fontFamily:
					theme.fontFamily,

				color:
					theme.colors.ink,
			}}
		>
			<PaperCard>
				<div
					style={{
						transform:
							`scale(${scale})`,

						textAlign: 'center',
					}}
				>
					<div
						style={{
							marginBottom: 45,

							fontSize:
								theme.ending.titleFontSize,

							fontWeight: 900,

							lineHeight: 1.2,

							letterSpacing: -3,

							whiteSpace: 'pre-line',
						}}
					>
						{scene.caption}
					</div>

					<div
						style={{
							fontSize:
								theme.ending.subtitleFontSize,

							fontWeight: 700,

							color:
								theme.colors.inkSoft,
						}}
					>
						댓글에 점수를 남겨주세요
					</div>
				</div>
			</PaperCard>
		</AbsoluteFill>
	);
};

export const QuizSceneRenderer: React.FC<
	QuizSceneRendererProps
> = ({
	scene,
	episodeTitle,
}) => {
	switch (scene.sceneType) {
		case 'intro':
			return (
				<IntroScene
					scene={scene}
					episodeTitle={episodeTitle}
				/>
			);

		case 'question':
			return (
				<QuestionScene scene={scene} />
			);

		case 'countdown':
			return (
				<CountdownScene scene={scene} />
			);

		case 'answer':
			return (
				<AnswerScene scene={scene} />
			);

		case 'ending':
			return (
				<EndingScene scene={scene} />
			);

		default:
			return (
				<AbsoluteFill
					style={{
						backgroundColor:
							quizTheme.colors.background,

						display: 'flex',
						alignItems: 'center',
						justifyContent: 'center',

						fontFamily:
							quizTheme.fontFamily,

						fontSize: 56,
						fontWeight: 800,

						color:
							quizTheme.colors.ink,
					}}
				>
					지원하지 않는 퀴즈 장면입니다.
				</AbsoluteFill>
			);
	}
};