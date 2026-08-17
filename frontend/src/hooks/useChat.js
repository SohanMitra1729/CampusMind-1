/**
 * src/hooks/useChat.js — Chat Sessions, Messages & RAG Query Hook
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { toast } from 'sonner';
import { sendChatQueryStreamApi, getChatsApi, deleteChatApi, getChatMessagesApi } from '../api/chat';

export function useChat(userId) {
  const [messages, setMessages] = useState([]);
  const [chatSessions, setChatSessions] = useState([]);
  const [activeChatId, setActiveChatId] = useState(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [selectedSource, setSelectedSource] = useState(null);
  const [chatToDelete, setChatToDelete] = useState(null);
  const [isDeletingChat, setIsDeletingChat] = useState(false);
  const messagesEndRef = useRef(null);

  const fetchChats = useCallback(async () => {
    try {
      const data = await getChatsApi();
      setChatSessions(data || []);
    } catch (e) {
      console.error('Failed to fetch chats', e);
      toast.error('Failed to load past conversations.');
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
      toast.error('Failed to load conversation history.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleNewChat = useCallback(() => {
    setActiveChatId(null);
    setMessages([]);
  }, []);

  const confirmDeleteChat = useCallback(async () => {
    if (!chatToDelete) return;
    setIsDeletingChat(true);

    try {
      await deleteChatApi(chatToDelete.id);
      setChatSessions((prev) => prev.filter((c) => c.id !== chatToDelete.id));
      if (activeChatId === chatToDelete.id) {
        handleNewChat();
      }
      toast.success('Conversation deleted.');
      setChatToDelete(null);
    } catch (err) {
      console.error("Failed to delete chat", err);
      toast.error(err.message || 'Failed to delete conversation.');
    } finally {
      setIsDeletingChat(false);
    }
  }, [chatToDelete, activeChatId, handleNewChat]);

  const handleDeleteChatPrompt = useCallback((e, chat) => {
    e.stopPropagation();
    setChatToDelete(chat);
  }, []);

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
    const botMessageId = crypto.randomUUID();

    // Create user message AND initial empty bot message for streaming tokens
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: botMessageId, role: 'bot', content: '', metadata: {} },
    ]);
    setInput('');
    setIsLoading(true);

    const metadata_filter = selectedSource ? { source: selectedSource } : null;
    setSelectedSource(null);

    try {
      const finalResult = await sendChatQueryStreamApi(
        inputText,
        activeChatId,
        metadata_filter,
        (token) => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === botMessageId
                ? { ...msg, content: msg.content + token }
                : msg
            )
          );
        }
      );

      // Attach final metadata/sources if available
      if (finalResult.sources && finalResult.sources.length > 0) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === botMessageId
              ? { ...msg, metadata: { ...msg.metadata, sources: finalResult.sources } }
              : msg
          )
        );
      }

      if (!activeChatId && finalResult.chat_id) {
        setActiveChatId(finalResult.chat_id);
        fetchChats();
      }
    } catch (error) {
      console.error('Chat query error:', error);
      toast.error(error.message || 'Failed to get response from CampusMind.');
      setMessages((prev) =>
        prev.map((msg) => {
          if (msg.id !== botMessageId) return msg;
          const prefix = msg.content ? `${msg.content}\n\n` : '';
          return {
            ...msg,
            isError: true,
            content: `${prefix}⚠️ *An error occurred while generating the response. Please try again.*`,
          };
        })
      );
    } finally {
      setIsLoading(false);
    }
  }, [input, selectedSource, activeChatId, fetchChats]);

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
    chatToDelete,
    setChatToDelete,
    isDeletingChat,
    confirmDeleteChat,
    fetchChats,
    loadChat,
    handleNewChat,
    handleDeleteChatPrompt,
    handleQuickAction,
    sendMessage,
  };
}
