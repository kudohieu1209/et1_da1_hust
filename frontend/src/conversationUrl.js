export function conversationIdFromUrl(urlValue) {
  return new URL(urlValue).searchParams.get('chat');
}

export function urlWithConversationId(urlValue, conversationId) {
  const url = new URL(urlValue);
  if (conversationId) {
    url.searchParams.set('chat', conversationId);
  } else {
    url.searchParams.delete('chat');
  }
  return url.toString();
}
