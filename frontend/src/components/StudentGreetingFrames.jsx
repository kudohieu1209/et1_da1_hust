import { useEffect, useId, useRef, useState, useSyncExternalStore } from 'react';

const reducedMotionQuery = '(prefers-reduced-motion: reduce)';
const getReducedMotion = () => window.matchMedia(reducedMotionQuery).matches;
const subscribeReducedMotion = callback => {
  const query = window.matchMedia(reducedMotionQuery);
  query.addEventListener('change', callback);
  return () => query.removeEventListener('change', callback);
};

function preload(src) {
  return new Promise(resolve => {
    const image = new Image();
    image.onload = () => image.decode().then(() => resolve(true), () => resolve(false));
    image.onerror = () => resolve(false);
    image.src = src;
  });
}

export default function StudentGreetingFrames({ mascot, language, playbackRate }) {
  const id = useId().replace(/:/g, '');
  const reduced = useSyncExternalStore(subscribeReducedMotion, getReducedMotion, () => true);
  const [ready, setReady] = useState(false);
  const [frame, setFrame] = useState(0);
  const [replay, setReplay] = useState(0);
  const playing = useRef(false);
  const { frames, timeline } = mascot.greeting;

  useEffect(() => {
    if (reduced) return undefined;
    let mounted = true;
    // Wait for every frame so a slow connection never produces a blank pose.
    Promise.all(frames.map(preload)).then(results => {
      if (mounted) setReady(results.every(Boolean));
    });
    return () => { mounted = false; };
  }, [frames, reduced]);

  useEffect(() => {
    setFrame(0);
    if (!ready || reduced) {
      playing.current = false;
      return undefined;
    }
    playing.current = true;
    const speed = Number.isFinite(playbackRate) && playbackRate > 0 ? playbackRate : 1;
    let timer;
    const advance = index => {
      setFrame(timeline[index].frame);
      if (index === timeline.length - 1) {
        playing.current = false;
        return;
      }
      // Chain relative delays: after a busy render, don't fire several overdue
      // absolute timers together and skip the intermediate lifting poses.
      timer = setTimeout(() => advance(index + 1), (timeline[index + 1].at - timeline[index].at) / speed);
    };
    timer = setTimeout(() => advance(1), timeline[1].at / speed);
    return () => {
      clearTimeout(timer);
      playing.current = false;
    };
  }, [ready, reduced, replay, playbackRate, timeline]);

  const greetAgain = () => {
    // Pointer-enter, focus and click may arrive together. Finish one gesture
    // before accepting another, rather than snapping back to the idle frame.
    if (ready && !reduced && !playing.current) setReplay(current => current + 1);
  };

  const visibleFrame = reduced ? 0 : frame;
  return (
    <button type="button" className="student-welcome" data-mascot={mascot.id}
      data-frame={visibleFrame}
      aria-label={language === 'vi' ? `${mascot.name.vi} Bách Khoa chào bạn — nhấn để chào lại` : `Your HUST ${mascot.name.en.toLowerCase()} — press to greet again`}
      onPointerEnter={greetAgain} onFocus={greetAgain} onClick={greetAgain}>
      <svg className="student-welcome__art" viewBox="250 0 700 1254" fill="none" aria-hidden="true">
        <defs>
          <clipPath id={`${id}-eyes`}>
            {mascot.eyes.map((eye, index) => <ellipse key={index} {...eye} />)}
          </clipPath>
        </defs>
        <g transform={`translate(${627 * (1 - mascot.scale)} ${1254 * (1 - mascot.scale)}) scale(${mascot.scale})`}>
          {frames.map((src, index) => (!reduced || index === 0) && (
            <image key={src} className="student-welcome__frame" href={src} width="1254" height="1254" opacity={index === visibleFrame ? 1 : 0} />
          ))}
          <image className="student-welcome__blink" href={mascot.blink} width="1254" height="1254" clipPath={`url(#${id}-eyes)`} />
        </g>
      </svg>
    </button>
  );
}
