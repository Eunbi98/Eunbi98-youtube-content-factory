import React from 'react';

import {
	AbsoluteFill,
	Sequence,
} from 'remotion';

import type {
	EpisodeTimeline,
} from '../types/timeline';

import {
	QuizSceneRenderer,
} from './QuizSceneRenderer';

export type QuizCompositionProps = {
	episodeId: string;
	timeline?: EpisodeTimeline;
};

export const QuizComposition: React.FC<
	QuizCompositionProps
> = ({
	timeline,
}) => {
	if (!timeline) {
		return (
			<AbsoluteFill
				style={{
					backgroundColor: '#6FB382',

					display: 'flex',
					alignItems: 'center',
					justifyContent: 'center',

					fontFamily:
						'Pretendard, "Noto Sans KR", Arial, sans-serif',

					fontSize: 54,
					fontWeight: 800,

					color: '#214F2A',
				}}
			>
				Quiz Timeline loading...
			</AbsoluteFill>
		);
	}

	return (
		<AbsoluteFill>
			{timeline.scenes.map((scene) => {
				const from = Math.round(
					scene.start *
						timeline.fps,
				);

				const durationInFrames =
					Math.max(
						1,
						Math.round(
							scene.duration *
								timeline.fps,
						),
					);

				return (
					<Sequence
						key={scene.id}
						from={from}
						durationInFrames={
							durationInFrames
						}
					>
						<QuizSceneRenderer
							scene={scene}
							episodeTitle={
								timeline.title
							}
						/>
					</Sequence>
				);
			})}
		</AbsoluteFill>
	);
};