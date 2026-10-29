import assert from 'node:assert/strict';
import test from 'node:test';

import { conversationIdFromUrl, urlWithConversationId } from './conversationUrl.js';

test('adds a conversation id while preserving unrelated query parameters', () => {
  const result = urlWithConversationId('https://advisor.test/app?lang=vi', 'conv-123');
  const url = new URL(result);

  assert.equal(url.searchParams.get('chat'), 'conv-123');
  assert.equal(url.searchParams.get('lang'), 'vi');
});

test('replaces an existing conversation id', () => {
  const result = urlWithConversationId('https://advisor.test/app?chat=old', 'new');
  assert.equal(conversationIdFromUrl(result), 'new');
});

test('removes the conversation id for a new chat', () => {
  const result = urlWithConversationId('https://advisor.test/app?chat=old&lang=en', null);
  const url = new URL(result);

  assert.equal(conversationIdFromUrl(result), null);
  assert.equal(url.searchParams.get('lang'), 'en');
});
