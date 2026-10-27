import { useSyncExternalStore } from 'react';
import { DEFAULT_MASCOT_ID, getMascot } from './mascots.js';
import { getMascotId, setMascot, subscribeMascot } from './mascotPreference.js';

export default function useMascot() {
  const id = useSyncExternalStore(subscribeMascot, getMascotId, () => DEFAULT_MASCOT_ID);
  return { mascot: getMascot(id), setMascot };
}
