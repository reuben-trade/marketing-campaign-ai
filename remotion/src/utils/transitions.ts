import { interpolate } from 'remotion';
import type { TransitionType } from '../types';

interface TransitionStyle {
  opacity?: number;
  scale?: number;
  translateX?: number;
  translateY?: number;
}

/**
 * Apply transition-in effect based on transition type
 */
export const applyTransitionIn = (
  type: TransitionType,
  localFrame: number,
  durationFrames: number,
  width: number,
  height: number
): TransitionStyle => {
  if (durationFrames === 0 || type === 'cut') {
    return {};
  }

  const progress = interpolate(localFrame, [0, durationFrames], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  switch (type) {
    case 'fade':
    case 'dissolve':
      return { opacity: progress };

    case 'wipe_right':
      return { translateX: interpolate(progress, [0, 1], [-width, 0]) };

    case 'wipe_left':
      return { translateX: interpolate(progress, [0, 1], [width, 0]) };

    case 'slide_up':
      return { translateY: interpolate(progress, [0, 1], [height, 0]) };

    case 'slide_down':
      return { translateY: interpolate(progress, [0, 1], [-height, 0]) };

    case 'zoom_in':
      return {
        scale: interpolate(progress, [0, 1], [0.5, 1]),
        opacity: progress,
      };

    case 'zoom_out':
      return {
        scale: interpolate(progress, [0, 1], [1.5, 1]),
        opacity: progress,
      };

    default:
      return {};
  }
};

/**
 * Apply transition-out effect based on transition type
 */
export const applyTransitionOut = (
  type: TransitionType,
  localFrame: number,
  segmentDuration: number,
  durationFrames: number,
  width: number,
  height: number
): TransitionStyle => {
  if (durationFrames === 0 || type === 'cut') {
    return {};
  }

  const transitionStart = segmentDuration - durationFrames;
  if (localFrame < transitionStart) {
    return {};
  }

  const progress = interpolate(
    localFrame,
    [transitionStart, segmentDuration],
    [0, 1],
    {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp',
    }
  );

  switch (type) {
    case 'fade':
    case 'dissolve':
      return { opacity: 1 - progress };

    case 'wipe_right':
      return { translateX: interpolate(progress, [0, 1], [0, width]) };

    case 'wipe_left':
      return { translateX: interpolate(progress, [0, 1], [0, -width]) };

    case 'slide_up':
      return { translateY: interpolate(progress, [0, 1], [0, -height]) };

    case 'slide_down':
      return { translateY: interpolate(progress, [0, 1], [0, height]) };

    case 'zoom_in':
      return {
        scale: interpolate(progress, [0, 1], [1, 1.5]),
        opacity: 1 - progress,
      };

    case 'zoom_out':
      return {
        scale: interpolate(progress, [0, 1], [1, 0.5]),
        opacity: 1 - progress,
      };

    default:
      return {};
  }
};
