import { useId, useState } from 'react';
import './StudentWelcome.css';

const CHARACTER = '/brand/hust-student-chibi.png';
const BLINK = '/brand/hust-student-chibi-blink.png';

export default function StudentWelcome({ language = 'vi' }) {
  const id = useId().replace(/:/g, '');
  const [wave, setWave] = useState(0);
  const waveAgain = () => setWave(current => current + 1);

  return (
    <button
      type="button"
      className="student-welcome"
      aria-label={language === 'vi' ? 'Sinh viên Bách Khoa chào bạn — nhấn để vẫy tay' : 'Your HUST student buddy — press to wave'}
      onPointerEnter={waveAgain}
      onFocus={waveAgain}
      onClick={waveAgain}
    >
      <svg className="student-welcome__art" viewBox="250 0 700 1254" fill="none" aria-hidden="true">
        <defs>
          {/* Keep the original PNG intact; only the hand layer moves at the wrist. */}
          <mask id={`${id}-body`} maskUnits="userSpaceOnUse" x="0" y="0" width="1254" height="1254">
            <rect width="1254" height="1254" fill="white" />
            <path d="M310 310H472V438L430 453H373L343 438Z" fill="black" />
          </mask>
          <clipPath id={`${id}-hand`}>
            <path d="M310 310H472V438L430 465H373L343 438Z" />
          </clipPath>
          <clipPath id={`${id}-eyes`}>
            <ellipse cx="569" cy="326" rx="57" ry="48" />
            <ellipse cx="708" cy="308" rx="55" ry="48" />
          </clipPath>
        </defs>

        <image href={CHARACTER} width="1254" height="1254" mask={`url(#${id}-body)`} />
        <image className="student-welcome__blink" href={BLINK} width="1254" height="1254" clipPath={`url(#${id}-eyes)`} />
        <g
          key={wave}
          className="student-welcome__hand"
          style={{ animationIterationCount: wave === 0 ? 2 : 1, animationDelay: wave === 0 ? '400ms' : '0ms' }}
        >
          <image href={CHARACTER} width="1254" height="1254" clipPath={`url(#${id}-hand)`} />
        </g>
      </svg>
    </button>
  );
}
