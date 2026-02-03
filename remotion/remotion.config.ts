import { Config } from '@remotion/cli/config';

// Set the entry point
Config.setEntryPoint('./src/Root.tsx');

// Increase memory for large video renders
Config.setChromiumOpenGlRenderer('angle');

// Output settings
Config.setCodec('h264');
Config.setVideoImageFormat('jpeg');

// Performance
Config.setConcurrency(4);
