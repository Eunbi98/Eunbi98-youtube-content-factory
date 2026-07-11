export type MediaType =
	| 'image'
	| 'video'
	| 'color';


export type CameraMotion =
	| 'static'
	| 'zoom_in'
	| 'zoom_out'
	| 'pan_left'
	| 'pan_right'
	| 'pan_up'
	| 'pan_down'
	| 'zoom_in_left'
	| 'zoom_in_right'
	| 'zoom_in_up'
	| 'zoom_in_down';


export type TransitionType =
	| 'cut'
	| 'fade'
	| 'slide_left'
	| 'slide_right'
	| 'zoom';


export type OverlayType =
	| 'none'
	| 'cinematic'
	| 'vignette'
	| 'dark';


export type SceneMedia = {
	type: MediaType;

	src?: string;

	fit?:
		| 'cover'
		| 'contain';

	position?: string;
};


/**
 * Edge TTS가 생성한 단어별 발화 시간입니다.
 *
 * 모든 시간은 해당 Scene의 오디오 시작점을 기준으로 한
 * 초 단위 상대 시간입니다.
 */
export type WordTiming = {
	text: string;

	offset: number;

	duration: number;

	end: number;
};


export type TimelineScene = {
	id: string;

	start: number;

	duration: number;

	title?: string;

	narration?: string;

	caption?: string;

	backgroundColor?: string;

	media?: SceneMedia;

	/**
	 * Remotion public 폴더를 기준으로 하는
	 * Scene 음성 파일 경로입니다.
	 *
	 * 예:
	 * ep008/scene_001.mp3
	 */
	audio?: string;

	/**
	 * 실제 MP3 재생 시간입니다.
	 */
	audioDuration?: number;

	/**
	 * TTS 타이밍 JSON 파일 경로입니다.
	 *
	 * 예:
	 * ep008/scene_001.timing.json
	 */
	timing?: string;

	/**
	 * Scene에 포함된 단어 타이밍 개수입니다.
	 */
	wordCount?: number;

	/**
	 * TTS 실제 발화 시점에 맞춘 단어별 시간 정보입니다.
	 */
	wordTimings?: WordTiming[];

	cameraMotion?: CameraMotion;

	transition?: TransitionType;

	transitionDuration?: number;

	overlay?: OverlayType;

	overlayOpacity?: number;
};


export type TimelineTheme = {
	backgroundColor?: string;

	titleColor?: string;

	captionColor?: string;

	accentColor?: string;
};


export type TimelineTTS = {
	provider?: string;

	sceneGapMs?: number;

	audioDirectory?: string;

	synchronized?: boolean;

	wordTiming?: boolean;

	timingVersion?: string;
};


export type EpisodeTimeline = {
	version?: string;

	episodeId: string;

	title: string;

	fps: number;

	width: number;

	height: number;

	totalDuration: number;

	theme?: TimelineTheme;

	tts?: TimelineTTS;

	bgm?: string;

	voice?: string;

	scenes: TimelineScene[];
};