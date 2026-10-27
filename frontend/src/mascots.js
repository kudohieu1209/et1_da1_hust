// Add a complete asset family here to make another companion available everywhere.
const GREETING_TIMELINE = [
  { at: 0, frame: 0 },
  { at: 350, frame: 1 },
  { at: 440, frame: 2 },
  { at: 540, frame: 3 },
  { at: 650, frame: 4 },
  { at: 790, frame: 5 },
  { at: 910, frame: 4 },
  { at: 990, frame: 6 },
  { at: 1110, frame: 4 },
  { at: 1190, frame: 5 },
  { at: 1310, frame: 4 },
  { at: 1390, frame: 6 },
  { at: 1510, frame: 4 },
  { at: 1630, frame: 3 },
  { at: 1740, frame: 2 },
  { at: 1840, frame: 1 },
  { at: 1930, frame: 0 },
];

export const MASCOTS = [
  {
    id: 'male',
    name: { vi: 'Chibi nam', en: 'Male chibi' },
    idle: '/brand/hust-student-male-idle.png',
    welcome: '/brand/hust-student-chibi.png',
    blink: '/brand/hust-student-chibi-blink.png',
    greeting: {
      frames: [
        '/brand/hust-student-male-idle.png',
        '/brand/hust-student-male-raise-start.png',
        '/brand/hust-student-male-raise-low.png',
        '/brand/hust-student-male-raise-high.png',
        '/brand/hust-student-chibi.png',
        '/brand/hust-student-male-wave-out.png',
        '/brand/hust-student-male-wave-in.png',
      ],
      timeline: GREETING_TIMELINE,
    },
    states: {
      transcript: '/brand/hust-student-transcript.png',
      offline: '/brand/hust-student-offline.png',
      achievement: '/brand/hust-student-achievement.png',
    },
    scale: 1,
    eyes: [{ cx: 569, cy: 326, rx: 57, ry: 48 }, { cx: 708, cy: 308, rx: 55, ry: 48 }],
  },
  {
    id: 'female',
    name: { vi: 'Chibi nữ', en: 'Female chibi' },
    idle: '/brand/hust-student-female-idle.png',
    welcome: '/brand/hust-student-female-welcome.png',
    blink: '/brand/hust-student-female-blink.png',
    greeting: {
      frames: [
        '/brand/hust-student-female-idle.png',
        '/brand/hust-student-female-raise-start.png',
        '/brand/hust-student-female-raise-low.png',
        '/brand/hust-student-female-raise-high.png',
        '/brand/hust-student-female-welcome.png',
        '/brand/hust-student-female-wave-out.png',
        '/brand/hust-student-female-wave-in.png',
      ],
      timeline: GREETING_TIMELINE,
    },
    states: {
      transcript: '/brand/hust-student-female-transcript.png',
      offline: '/brand/hust-student-female-offline.png',
      achievement: '/brand/hust-student-female-achievement.png',
    },
    // Keep the small height difference approved in the character comparison.
    scale: 0.97,
    eyes: [{ cx: 550, cy: 301, rx: 46, ry: 40 }, { cx: 677, cy: 276, rx: 49, ry: 40 }],
  },
];

export const DEFAULT_MASCOT_ID = 'male';

export function getMascot(id) {
  return MASCOTS.find(mascot => mascot.id === id) || MASCOTS[0];
}
