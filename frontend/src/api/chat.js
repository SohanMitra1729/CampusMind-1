/**
 * src/api/chat.js — Chat & RAG API Methods
 */

import { apiClient } from './client';

export async function sendChatQueryApi(query, chatId = null, metadataFilter = null) {
  return apiClient('/api/chat', {
    method: 'POST',
    body: JSON.stringify({
      query,
      chat_id: chatId,
      metadata_filter: metadataFilter,
    }),
  });
}

export async function getChatsApi() {
  return apiClient('/api/chats', {
    method: 'GET',
  });
}

export async function deleteChatApi(chatId) {
  return apiClient(`/api/chats/${chatId}`, {
    method: 'DELETE',
  });
}

export async function getChatMessagesApi(chatId) {
  return apiClient(`/api/chats/${chatId}/messages`, {
    method: 'GET',
  });
}
