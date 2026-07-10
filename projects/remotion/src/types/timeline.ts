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
	| 'pan_down';

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
	fit?: 'cover' | 'contain';
	position?: string;
};

export type TimelineScene = {
	id: string;

	start: number;
	duration: number;

	title?: string;
	caption?: string;

	backgroundColor?: string;

	media?: SceneMedia;

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

export type EpisodeTimeline = {
	episodeId: string;
	title: string;

	fps: number;
	width: number;
	height: number;
	totalDuration: number;

	theme?: TimelineTheme;
	scenes: TimelineScene[];
};