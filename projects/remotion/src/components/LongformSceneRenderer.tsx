import React from 'react';
import {
	AbsoluteFill,
	interpolate,
	useCurrentFrame,
	useVideoConfig,
} from 'remotion';

import type {TimelineScene} from '../types/timeline';
import {VisualLayer} from './VisualLayer';
import {OverlayLayer} from './OverlayLayer';
import {ResponsiveCaptionLayer} from './ResponsiveCaptionLayer';


type Props = {
	scene: TimelineScene;
	durationInFrames: number;
	captionColor: string;
	index: number;
	totalScenes: number;
};

const ACCENT = '#D7B77A';
const PANEL = 'rgba(8, 12, 20, 0.82)';
const PANEL_SOFT = 'rgba(8, 12, 20, 0.62)';

const getChapter = (index: number, totalScenes: number) => {
	if (index <= 0 || index >= totalScenes - 1) return null;
	return Math.ceil(index / 3);
};

const getPhase = (index: number) => {
	if (index <= 0) return 'intro' as const;
	return (index - 1) % 3;
};

const titleStyle: React.CSSProperties = {
	fontFamily: '"Pretendard", "Noto Sans KR", Arial, sans-serif',
	fontWeight: 850,
	letterSpacing: '-0.04em',
	lineHeight: 1.12,
	wordBreak: 'keep-all',
};

export const LongformSceneRenderer: React.FC<Props> = ({
	scene,
	durationInFrames,
	captionColor,
	index,
	totalScenes,
}) => {
	const frame = useCurrentFrame();
	const {fps} = useVideoConfig();
	const chapter = getChapter(index, totalScenes);
	const phase = getPhase(index);
	const isIntro = index === 0;
	const isOutro = index === totalScenes - 1;
	const progress = totalScenes <= 1 ? 1 : index / (totalScenes - 1);

	const enter = interpolate(
		frame,
		[0, Math.max(1, Math.round(fps * 0.45))],
		[0, 1],
		{extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
	);
	const translateY = interpolate(enter, [0, 1], [24, 0]);

	const commonChrome = (
		<>
			<div
				style={{
					position: 'absolute',
					top: 34,
					left: 54,
					right: 54,
					display: 'flex',
					alignItems: 'center',
					justifyContent: 'space-between',
					zIndex: 40,
					fontFamily: '"Pretendard", "Noto Sans KR", Arial, sans-serif',
					fontSize: 18,
					fontWeight: 700,
					letterSpacing: '0.08em',
					textTransform: 'uppercase',
					color: 'rgba(255,255,255,0.72)',
				}}
			>
				<div>WORLD BITE · SPACE FILE</div>
				<div>{chapter ? `CHAPTER ${String(chapter).padStart(2, '0')}` : isOutro ? 'EPILOGUE' : 'PROLOGUE'}</div>
			</div>
			<div
				style={{
					position: 'absolute',
					left: 0,
					right: 0,
					bottom: 0,
					height: 5,
					backgroundColor: 'rgba(255,255,255,0.13)',
					zIndex: 60,
				}}
			>
				<div style={{width: `${Math.max(3, progress * 100)}%`, height: '100%', backgroundColor: ACCENT}} />
			</div>
		</>
	);

	if (isIntro || isOutro || phase === 0) {
		return (
			<AbsoluteFill style={{backgroundColor: '#090D15'}}>
				<VisualLayer scene={scene} durationInFrames={durationInFrames} />
				<div
					style={{
						position: 'absolute', inset: 0,
						background: 'linear-gradient(90deg, rgba(5,9,16,0.93) 0%, rgba(5,9,16,0.78) 36%, rgba(5,9,16,0.18) 72%, rgba(5,9,16,0.08) 100%)',
						zIndex: 20,
					}}
				/>
				{commonChrome}
				<div
					style={{
						position: 'absolute',
						left: 92,
						top: isIntro ? 230 : 205,
						width: isIntro || isOutro ? 900 : 820,
						zIndex: 45,
						opacity: enter,
						transform: `translateY(${translateY}px)`,
					}}
				>
					{chapter ? (
						<div style={{fontSize: 92, fontWeight: 300, color: ACCENT, lineHeight: 0.95, marginBottom: 24}}>
							{String(chapter).padStart(2, '0')}
						</div>
					) : null}
					<div style={{...titleStyle, fontSize: isIntro ? 72 : 60, color: '#F5F1E9', maxWidth: 900}}>
						{scene.title}
					</div>
					<div style={{width: 110, height: 4, backgroundColor: ACCENT, marginTop: 30}} />
					<div style={{marginTop: 22, fontSize: 23, fontWeight: 600, color: 'rgba(255,255,255,0.68)', letterSpacing: '0.02em'}}>
						{isIntro ? '7개의 단서로 다시 보는 우주의 이상한 순간들' : isOutro ? '우주는 답보다 질문을 더 많이 남긴다' : '관측 → 해석 → 아직 남은 질문'}
					</div>
				</div>
				<ResponsiveCaptionLayer
					caption={scene.caption}
					color={captionColor}
					durationInFrames={durationInFrames}
					wordTimings={scene.wordTimings}
				/>
			</AbsoluteFill>
		);
	}

	const panelOnLeft = phase === 1;
	return (
		<AbsoluteFill style={{backgroundColor: '#090D15'}}>
			<VisualLayer scene={scene} durationInFrames={durationInFrames} />
			<OverlayLayer scene={scene} />
			<div
				style={{
					position: 'absolute', inset: 0,
					background: panelOnLeft
						? 'linear-gradient(90deg, rgba(5,9,16,0.90) 0%, rgba(5,9,16,0.72) 38%, rgba(5,9,16,0.10) 68%, rgba(5,9,16,0.05) 100%)'
						: 'linear-gradient(270deg, rgba(5,9,16,0.90) 0%, rgba(5,9,16,0.72) 38%, rgba(5,9,16,0.10) 68%, rgba(5,9,16,0.05) 100%)',
					zIndex: 20,
				}}
			/>
			{commonChrome}

			<div
				style={{
					position: 'absolute',
					top: 118,
					bottom: 180,
					width: 650,
					[panelOnLeft ? 'left' : 'right']: 72,
					zIndex: 45,
					display: 'flex',
					flexDirection: 'column',
					justifyContent: 'center',
					opacity: enter,
					transform: `translateY(${translateY}px)`,
				}}
			>
				<div
					style={{
						alignSelf: 'flex-start',
						padding: '8px 14px',
						border: `1px solid ${ACCENT}`,
						borderRadius: 999,
						fontSize: 15,
						fontWeight: 800,
						letterSpacing: '0.12em',
						color: ACCENT,
						backgroundColor: 'rgba(8,12,20,0.55)',
						marginBottom: 24,
					}}
				>
					{phase === 1 ? 'WHAT WE KNOW' : 'WHY IT MATTERS'}
				</div>
				<div style={{...titleStyle, fontSize: 48, color: '#F7F4ED'}}>{scene.title}</div>
				<div style={{marginTop: 26, padding: '24px 26px', borderRadius: 18, backgroundColor: phase === 1 ? PANEL : PANEL_SOFT, border: '1px solid rgba(255,255,255,0.10)', boxShadow: '0 18px 60px rgba(0,0,0,0.25)'}}>
					<div style={{fontSize: 21, lineHeight: 1.55, color: 'rgba(255,255,255,0.82)', fontWeight: 560}}>
						{phase === 1 ? '관측된 사실을 먼저 보고, 다음 장면에서 왜 그런지 해석합니다.' : '관측만으로 끝내지 않고 이 현상이 우리 이해를 어떻게 바꾸는지 봅니다.'}
					</div>
				</div>
			</div>

			<ResponsiveCaptionLayer
				caption={scene.caption}
				color={captionColor}
				durationInFrames={durationInFrames}
				wordTimings={scene.wordTimings}
			/>
		</AbsoluteFill>
	);
};
