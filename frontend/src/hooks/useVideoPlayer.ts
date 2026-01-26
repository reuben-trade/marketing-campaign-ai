'use client';

import { useCallback, useRef, useState, useEffect } from 'react';
import type { EnhancedNarrativeBeat } from '@/types/analysis';

interface UseVideoPlayerOptions {
  timeline?: EnhancedNarrativeBeat[];
  onBeatChange?: (beat: EnhancedNarrativeBeat | null) => void;
}

export function useVideoPlayer(options: UseVideoPlayerOptions = {}) {
  const { timeline = [], onBeatChange } = options;
  const videoRef = useRef<HTMLVideoElement>(null);
  const beatEndListenerRef = useRef<(() => void) | null>(null);
  const [currentBeat, setCurrentBeat] = useState<EnhancedNarrativeBeat | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  // Parse MM:SS to seconds
  const parseTimestamp = useCallback((timestamp: string): number => {
    const parts = timestamp.split(':');
    if (parts.length === 2) {
      return parseInt(parts[0], 10) * 60 + parseInt(parts[1], 10);
    }
    return 0;
  }, []);

  // Format seconds to MM:SS
  const formatTimestamp = useCallback((seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }, []);

  // Find current beat based on playhead position
  const findCurrentBeat = useCallback(
    (time: number): EnhancedNarrativeBeat | null => {
      for (const beat of timeline) {
        const start = parseTimestamp(beat.start_time);
        const end = parseTimestamp(beat.end_time);
        if (time >= start && time < end) {
          return beat;
        }
      }
      return null;
    },
    [timeline, parseTimestamp]
  );

  // Update current beat on time change
  useEffect(() => {
    const beat = findCurrentBeat(currentTime);
    if (beat !== currentBeat) {
      setCurrentBeat(beat);
      onBeatChange?.(beat);
    }
  }, [currentTime, findCurrentBeat, currentBeat, onBeatChange]);

  // Play specific beat (highlighted clip)
  const playBeat = useCallback(
    (beat: EnhancedNarrativeBeat) => {
      if (!videoRef.current) return;

      // Clean up previous beat-end listener
      if (beatEndListenerRef.current) {
        beatEndListenerRef.current();
        beatEndListenerRef.current = null;
      }

      const startSeconds = parseTimestamp(beat.start_time);
      const endSeconds = parseTimestamp(beat.end_time);

      videoRef.current.currentTime = startSeconds;
      setCurrentBeat(beat);

      // Play and handle the promise (browsers require this)
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise
          .then(() => {
            setIsPlaying(true);
          })
          .catch(() => {
            // Autoplay was prevented - user needs to interact first
            setIsPlaying(false);
          });
      }

      // Stop at beat end
      const handleTimeUpdate = () => {
        if (videoRef.current && videoRef.current.currentTime >= endSeconds) {
          videoRef.current.pause();
          setIsPlaying(false);
          videoRef.current.removeEventListener('timeupdate', handleTimeUpdate);
          beatEndListenerRef.current = null;
        }
      };
      videoRef.current.addEventListener('timeupdate', handleTimeUpdate);
      beatEndListenerRef.current = () => {
        videoRef.current?.removeEventListener('timeupdate', handleTimeUpdate);
      };
    },
    [parseTimestamp]
  );

  // Navigate to next/previous beat
  const navigateBeat = useCallback(
    (direction: 'next' | 'prev') => {
      if (!timeline.length) return;

      if (!currentBeat) {
        playBeat(timeline[0]);
        return;
      }

      const currentIndex = timeline.findIndex(
        (b) => b.start_time === currentBeat.start_time
      );

      if (direction === 'next' && currentIndex < timeline.length - 1) {
        playBeat(timeline[currentIndex + 1]);
      } else if (direction === 'prev' && currentIndex > 0) {
        playBeat(timeline[currentIndex - 1]);
      }
    },
    [currentBeat, timeline, playBeat]
  );

  // Seek to specific time
  const seekTo = useCallback((time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  }, []);

  // Toggle play/pause
  const togglePlayPause = useCallback(() => {
    if (!videoRef.current) return;

    if (videoRef.current.paused) {
      // Clean up any beat-end listener so continuous play works
      if (beatEndListenerRef.current) {
        beatEndListenerRef.current();
        beatEndListenerRef.current = null;
      }
      const playPromise = videoRef.current.play();
      if (playPromise !== undefined) {
        playPromise.then(() => setIsPlaying(true)).catch(() => setIsPlaying(false));
      }
    } else {
      videoRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  // Video event handlers
  const handleTimeUpdate = useCallback(() => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  }, []);

  const handleLoadedMetadata = useCallback(() => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
    }
  }, []);

  const handlePlay = useCallback(() => setIsPlaying(true), []);
  const handlePause = useCallback(() => setIsPlaying(false), []);

  return {
    videoRef,
    currentBeat,
    isPlaying,
    currentTime,
    duration,
    playBeat,
    navigateBeat,
    seekTo,
    togglePlayPause,
    parseTimestamp,
    formatTimestamp,
    findCurrentBeat,
    // Event handlers to attach to video element
    videoEventHandlers: {
      onTimeUpdate: handleTimeUpdate,
      onLoadedMetadata: handleLoadedMetadata,
      onPlay: handlePlay,
      onPause: handlePause,
    },
  };
}
