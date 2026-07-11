import type {CameraMotion} from '../types/timeline';

export type MotionPreset = {
	scale?: [number, number];
	x?: [number, number];
	y?: [number, number];
	transformOrigin?: string;
};

export const motionPresets: Record<
	CameraMotion,
	MotionPreset
> = {
	static: {},

	zoom_in: {
		scale: [1.02, 1.12],
	},

	zoom_out: {
		scale: [1.12, 1.02],
	},

	pan_left: {
		scale: [1.1, 1.1],
		x: [3.5, -3.5],
	},

	pan_right: {
		scale: [1.1, 1.1],
		x: [-3.5, 3.5],
	},

	pan_up: {
		scale: [1.1, 1.1],
		y: [3.5, -3.5],
	},

	pan_down: {
		scale: [1.1, 1.1],
		y: [-3.5, 3.5],
	},
    	zoom_in_left: {
		scale: [1.03, 1.14],
		x: [1.5, -2.5],
	},

	zoom_in_right: {
		scale: [1.03, 1.14],
		x: [-1.5, 2.5],
	},

	zoom_in_up: {
		scale: [1.03, 1.14],
		y: [1.5, -2.5],
	},

	zoom_in_down: {
		scale: [1.03, 1.14],
		y: [-1.5, 2.5],
	},
};