/**
 * src/api/chat.js — Chat & RAG API Methods
 */

import { apiClient, apiStreamClient } from './client';

export async function sendChatQueryStreamApi(query, chatId = null, metadataFilter = null, onChunk = () => {}) {
  const response = await apiStreamClient('/api/chat/stream', {
    method: 'POST',
    body: JSON.stringify({
      query,
      chat_id: chatId,
      metadata_filter: metadataFilter,
    }),
  });


  const reader = response.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  let finalResult = { chat_id: null, title: null, sources: [] };

  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop(); // Keep incomplete line chunk in buffer

    for (const line of lines) {
      const trimmed = line.trim();
      if (trimmed.startsWith('data: ')) {
        const jsonStr = trimmed.slice(6);
        try {
          const payload = JSON.parse(jsonStr);
          if (payload.token) {
            onChunk(payload.token);
          }
          if (payload.done) {
            finalResult = {
              chat_id: payload.chat_id,
              title: payload.title,
              sources: payload.sources || [],
            };
          }
        } catch (e) {
          // Ignore JSON parse errors for malformed SSE chunks
        }
      }
    }
  }

  if (buffer && buffer.trim().startsWith('data: ')) {
    try {
      const payload = JSON.parse(buffer.trim().slice(6));
      if (payload.token) onChunk(payload.token);
      if (payload.done) {
        finalResult = {
          chat_id: payload.chat_id,
          title: payload.title,
          sources: payload.sources || [],
        };
      }
    } catch (e) {}
  }

  return finalResult;
}


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
