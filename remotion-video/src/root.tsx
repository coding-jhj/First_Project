import React from 'react';
import {Composition} from 'remotion';
import {VoiceGuideDemo} from './voiceguide-demo';

export const Root: React.FC = () => {
  return (
    <Composition
      id="VoiceGuideDemo"
      component={VoiceGuideDemo}
      durationInFrames={15900}
      fps={30}
      width={1920}
      height={1080}
      defaultProps={{presenter: 'VoiceGuide 3팀'}}
    />
  );
};
