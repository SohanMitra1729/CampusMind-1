/**
 * src/hooks/useNotifications.js — Student Notification Center Hook (Polling & Mark Read)
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';
import { getNotificationsApi, markNotificationReadApi, markAllNotificationsReadApi } from '../api/notices';

function formatNotifTime(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'Just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function useNotifications(userId) {
  const [notifications, setNotifications] = useState([]);
  const [showNotifications, setShowNotifications] = useState(false);
  const [notifFilter, setNotifFilter] = useState('all');
  const notifPollRef = useRef(null);
  const notifRef = useRef(null);

  const fetchNotifications = useCallback(async () => {
    if (!userId) return;
    try {
      const data = await getNotificationsApi();
      if (Array.isArray(data)) {
        setNotifications(data.map(n => ({
          id:      n.id,
          title:   n.notification_title,
          message: n.notification_message,
          time:    formatNotifTime(n.created_at),
          unread:  !n.is_read,
          icon:    n.icon || '📢',
        })));
      }
    } catch (e) {
      console.error('Failed to fetch notifications', e);
    }
  }, [userId]);

  useEffect(() => {
    let isMounted = true;
    const initNotifs = async () => {
      if (isMounted && userId) {
        await fetchNotifications();
      }
    };
    initNotifs();
    if (userId) {
      notifPollRef.current = setInterval(fetchNotifications, 30000);
    }
    return () => {
      isMounted = false;
      if (notifPollRef.current) clearInterval(notifPollRef.current);
    };
  }, [userId, fetchNotifications]);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
    };
    if (showNotifications) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [showNotifications]);

  const markAllRead = useCallback(async () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
    try {
      await markAllNotificationsReadApi();
      toast.success('All notifications marked as read.');
    } catch (e) {
      console.error('Failed to mark all read', e);
      toast.error('Failed to update notifications.');
    }
  }, []);

  const toggleRead = useCallback(async (id) => {
    const notif = notifications.find(n => n.id === id);
    if (!notif) return;
    setNotifications(prev => prev.map(n => n.id === id ? { ...n, unread: !n.unread } : n));
    if (notif.unread) {
      try {
        await markNotificationReadApi(id);
      } catch (e) {
        console.error('Failed to mark notification read', e);
        toast.error('Failed to update notification state.');
      }
    }
  }, [notifications]);

  const unreadCount = notifications.filter(n => n.unread).length;
  const filteredNotifs = notifFilter === 'all' ? notifications : notifications.filter(n => n.unread);

  return {
    notifications,
    filteredNotifs,
    unreadCount,
    showNotifications,
    setShowNotifications,
    notifFilter,
    setNotifFilter,
    notifRef,
    fetchNotifications,
    markAllRead,
    toggleRead,
  };
}
