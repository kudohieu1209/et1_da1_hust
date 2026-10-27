import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import test from 'node:test';
import { MASCOTS } from '../src/mascots.js';

let instance = 0;
async function setup(t, initial = null, blocked = false) {
  const previousWindow = globalThis.window;
  const browser = new EventTarget();
  let saved = initial;
  browser.localStorage = {
    getItem() { if (blocked) throw new Error('Storage unavailable'); return saved; },
    setItem(_key, value) { if (blocked) throw new Error('Storage unavailable'); saved = value; },
  };
  globalThis.window = browser;
  t.after(() => { globalThis.window = previousWindow; });
  const store = await import(`../src/mascotPreference.js?test=${instance++}`);
  return { ...store, browser, saved: () => saved, externalChange(value, key = store.MASCOT_STORAGE_KEY) {
    saved = value;
    browser.dispatchEvent(Object.assign(new Event('storage'), { key }));
  } };
}

test('every selectable character has a complete, existing asset family', () => {
  for (const mascot of MASCOTS) {
    assert.ok(mascot.greeting, `${mascot.id} must provide a frame greeting`);
    for (const asset of [mascot.idle, mascot.welcome, mascot.blink, ...Object.values(mascot.states), ...(mascot.greeting?.frames || [])]) {
      assert.ok(existsSync(new URL(`../public${asset}`, import.meta.url)), asset);
    }
  }
});

test('frame greetings start and finish idle with strictly ordered, valid poses', () => {
  for (const mascot of MASCOTS.filter(option => option.greeting)) {
    const { frames, timeline } = mascot.greeting;
    assert.equal(timeline[0].at, 0);
    assert.equal(timeline[0].frame, 0);
    assert.equal(timeline.at(-1).frame, 0);
    const used = new Set();
    timeline.forEach((step, index) => {
      assert.ok(Number.isInteger(step.frame) && step.frame >= 0 && step.frame < frames.length);
      if (index > 0) assert.ok(step.at > timeline[index - 1].at);
      used.add(step.frame);
    });
    assert.equal(used.size, frames.length, 'every generated frame should be used');
  }
});

test('a saved female selection survives loading the store', async t => {
  const store = await setup(t, 'female');
  assert.equal(store.getMascotId(), 'female');
});

test('old browsers without a choice and invalid saved IDs use the existing male', async t => {
  const empty = await setup(t);
  assert.equal(empty.getMascotId(), 'male');
  const invalid = await setup(t, 'removed-character');
  assert.equal(invalid.getMascotId(), 'male');
});

test('selecting a character saves it and notifies all mounted consumers', async t => {
  const store = await setup(t);
  let updates = 0;
  const unsubscribeA = store.subscribeMascot(() => updates++);
  const unsubscribeB = store.subscribeMascot(() => updates++);
  store.setMascot('female');
  assert.equal(store.getMascotId(), 'female');
  assert.equal(store.saved(), 'female');
  assert.equal(updates, 2);
  store.setMascot('female');
  assert.equal(updates, 2);
  unsubscribeA(); unsubscribeB();
});

test('blocked storage still permits changing the character and remounting', async t => {
  const store = await setup(t, null, true);
  const unsubscribe = store.subscribeMascot(() => {});
  store.setMascot('female');
  assert.equal(store.getMascotId(), 'female');
  unsubscribe();
  const unsubscribeAgain = store.subscribeMascot(() => {});
  assert.equal(store.getMascotId(), 'female');
  unsubscribeAgain();
});

test('another tab updates the selection; clearing storage returns to the default', async t => {
  const store = await setup(t);
  const unsubscribe = store.subscribeMascot(() => {});
  store.externalChange('female');
  assert.equal(store.getMascotId(), 'female');
  store.externalChange(null, null);
  assert.equal(store.getMascotId(), 'male');
  unsubscribe();
  store.externalChange('female');
  const unsubscribeAgain = store.subscribeMascot(() => {});
  assert.equal(store.getMascotId(), 'female');
  unsubscribeAgain();
});
