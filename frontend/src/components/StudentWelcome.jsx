import { getMascot } from '../mascots';
import useMascot from '../useMascot';
import StudentGreetingFrames from './StudentGreetingFrames';
import './StudentWelcome.css';

export default function StudentWelcome({ language = 'vi', mascotId, playbackRate = 1 }) {
  const { mascot: selected } = useMascot();
  const mascot = mascotId ? getMascot(mascotId) : selected;
  return <StudentGreetingFrames key={mascot.id} mascot={mascot} language={language} playbackRate={playbackRate} />;
}
