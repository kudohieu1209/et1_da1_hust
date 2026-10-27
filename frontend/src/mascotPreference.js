import { DEFAULT_MASCOT_ID, getMascot } from './mascots.js';

export const MASCOT_STORAGE_KEY = 'hust_advisor_mascot';

function readSavedMascot() {
  try {
    return getMascot(window.localStorage.getItem(MASCOT_STORAGE_KEY)).id;
  } catch {
    return null;
  }
}

let persistedId = readSavedMascot();
let currentId = persistedId ?? DEFAULT_MASCOT_ID;
const listeners = new Set();

export function getMascotId() {
  return currentId;
}

function notify() {
  for (const listener of listeners) listener();
}

export function setMascot(id) {
  const nextId = getMascot(id).id;
  if (nextId === currentId) return;
  currentId = nextId;
  try {
    window.localStorage.setItem(MASCOT_STORAGE_KEY, nextId);
    persistedId = nextId;
  } catch {
    // Keep the choice usable for this session when browser storage is blocked/full.
  }
  notify();
}

function handleStorage(event) {
  if (event.key !== null && event.key !== MASCOT_STORAGE_KEY) return;
  const nextId = readSavedMascot();
  if (nextId === null) return;
  persistedId = nextId;
  if (nextId === currentId) return;
  currentId = nextId;
  notify();
}

export function subscribeMascot(listener) {
  if (listeners.size === 0) {
    window.addEventListener('storage', handleStorage);
    // Also catch changes from another tab while no mascot was mounted.
    const savedId = readSavedMascot();
    if (savedId !== null && savedId !== persistedId) {
      persistedId = savedId;
      currentId = savedId;
    }
  }
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) window.removeEventListener('storage', handleStorage);
  };
}
