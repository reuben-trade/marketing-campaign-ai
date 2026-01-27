import React from 'react';
import { registerVerticalAd } from './compositions/VerticalAd';
import { registerHorizontalAd } from './compositions/HorizontalAd';
import { registerSquareAd } from './compositions/SquareAd';

/**
 * Root component for Remotion Studio.
 * Registers all available compositions.
 */
export const RemotionRoot: React.FC = () => {
  return (
    <>
      {registerVerticalAd()}
      {registerHorizontalAd()}
      {registerSquareAd()}
    </>
  );
};
