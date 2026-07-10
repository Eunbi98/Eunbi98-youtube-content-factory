import React from 'react';

import {ep005Theme} from '../theme/ep005Theme';

type TitleLayerProps = {
	title: string;
	color?: string;
};

export const TitleLayer: React.FC<
	TitleLayerProps
> = ({title, color}) => {
	return (
		<div
			style={{
				position: 'absolute',

				top: ep005Theme.title.top,
				left: ep005Theme.title.left,
				right: ep005Theme.title.right,
				height: ep005Theme.title.height,

				display: 'flex',
				alignItems: 'center',
				justifyContent: 'center',

				fontFamily:
					ep005Theme.fontFamily,

				fontSize:
					ep005Theme.title.fontSize,

				fontWeight:
					ep005Theme.title.fontWeight,

				lineHeight:
					ep005Theme.title.lineHeight,

				letterSpacing:
					ep005Theme.title.letterSpacing,

				textAlign:
					ep005Theme.title.textAlign,

				color:
					color ??
					ep005Theme.titleColor,

				textShadow:
					ep005Theme.title.textShadow,

				whiteSpace: 'pre-wrap',
				wordBreak: 'keep-all',

				zIndex: 30,
			}}
		>
			{title}
		</div>
	);
};