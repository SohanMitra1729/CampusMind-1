/**
 * src/hooks/useChat.js — Chat Sessions, Messages & RAG Query Hook
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { sendChatQueryApi, getChatsApi, deleteChatApi, getChatMessagesApi } from '../api/chat';

export function useChat(userId, onComplaintDetect) {
  const [messages, setMessages] = useState([]);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const messagesEndRef = useRef(null);

  const fetchChats = useCallback(async () => {
    try {
      const data = await getChatsApi();
      setChatSessions(data || []);
    } catch (e) {
      console.error('Failed to fetch chats', e);
    }
  }, []);

  useEffect(() => {
    let isMounted = true;
    const initChats = async () => {
      if (isMounted && userId) {
        await fetchChats();
      }
    };
    initChats();
    return () => { isMounted = false; };
  }, [userId, fetchChats]);

  const loadChat = useCallback(async (chatId) => {
    setActiveChatId(chatId);
    setMessages([]);
    setIsLoading(true);
    try {
      const data = await getChatMessagesApi(chatId);
      // Ensure every message has a stable id for React key
      setMessages((data || []).map((m, i) => ({ id: m.id ?? `loaded-${i}`, ...m })));
    } catch (e) {
      console.error('Failed to load chat messages', e);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setActiveChatId(null);
    setMessages([]);
  }, []);

  const handleDeleteChat = useCallback(async (e, chatId) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this conversation?")) return;

    try {
      await deleteChatApi(chatId);
      setChatSessions((prev) => prev.filter((c) => c.id !== chatId));
      if (activeChatId === chatId) {
        handleNewChat();
      }
    } catch (err) {
      console.error("Failed to delete chat", err);
    }
  }, [activeChatId, handleNewChat]);

  const handleQuickAction = useCallback((text, source) => {
    setInput(text);
    setSelectedSource(source);
  }, []);

  // Clear the source filter if the user manually edits the input after
  // clicking a quick action — avoids filtering RAG by the wrong source.
  const handleInputChange = useCallback((value) => {
    setInput(value);
    // If input diverges from what the quick action set, clear the source filter
    setSelectedSource(null);
  }, []);

  const sendMessage = useCallback(async (e) => {
    if (e) e.preventDefault();
    if (!input.trim()) return;

    const inputText = input;
    const userMessage = { id: crypto.randomUUID(), role: 'user', content: inputText };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setSelectedSource(null); // Always clear source on send

    const metadata_filter = selectedSource ? { source: selectedSource } : null;
    setSelectedSource(null);

    if (userId && onComplaintDetect) {
      onComplaintDetect(inputText);
    }

    try {
      const data = await sendChatQueryApi(inputText, activeChatId, metadata_filter);
      const botMessage = {
        id: data.message_id ?? crypto.randomUUID(),
        role: 'bot',
        content: data.answer,
        context: data.context,
        metadata: data.metadata,
      };

      setMessages((prev) => [...prev, botMessage]);

      if (data.chat_id) {
        if (!activeChatId) {
          setActiveChatId(data.chat_id);
        }
        fetchChats();
      }
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = {
        id: crypto.randomUUID(),
        role: 'bot',
        content: 'Sorry, I encountered an error. Please try again later. Is the backend running?',
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [input, selectedSource, userId, onComplaintDetect, activeChatId, fetchChats]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  return {
    messages,
    chatSessions,
    activeChatId,
    input,
    setInput,
    handleInputChange,
    isLoading,
    messagesEndRef,
    fetchChats,
    loadChat,
    handleNewChat,
    handleDeleteChat,
    handleQuickAction,
    sendMessage,
  };
}
