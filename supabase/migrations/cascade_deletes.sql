-- =============================================================================
-- CampusMind PostgreSQL Cascade Deletes Migration
-- Ensures all related rows (messages, chats, complaints, votes, notifications)
-- automatically cascade-delete when a parent chat, complaint, notice, or user is deleted.
-- =============================================================================

-- 1. Messages -> Chats (When a chat is deleted, delete all its messages)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'messages_chat_id_fkey' AND table_name = 'messages'
    ) THEN
        ALTER TABLE public.messages DROP CONSTRAINT messages_chat_id_fkey;
    END IF;
    
    ALTER TABLE public.messages
    ADD CONSTRAINT messages_chat_id_fkey
    FOREIGN KEY (chat_id)
    REFERENCES public.chats(id)
    ON DELETE CASCADE;
END $$;

-- 2. Chats -> Profiles / Auth Users (When a user is deleted, delete all their chats)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'chats_user_id_fkey' AND table_name = 'chats'
    ) THEN
        ALTER TABLE public.chats DROP CONSTRAINT chats_user_id_fkey;
    END IF;

    ALTER TABLE public.chats
    ADD CONSTRAINT chats_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES public.profiles(id)
    ON DELETE CASCADE;
END $$;

-- 3. Profiles -> auth.users (When an auth user is deleted, delete their profile)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'profiles_id_fkey' AND table_name = 'profiles'
    ) THEN
        ALTER TABLE public.profiles DROP CONSTRAINT profiles_id_fkey;
    END IF;

    ALTER TABLE public.profiles
    ADD CONSTRAINT profiles_id_fkey
    FOREIGN KEY (id)
    REFERENCES auth.users(id)
    ON DELETE CASCADE;
END $$;

-- 4. Complaints -> Profiles (When a user is deleted, delete their filed complaints)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'complaints_user_id_fkey' AND table_name = 'complaints'
    ) THEN
        ALTER TABLE public.complaints DROP CONSTRAINT complaints_user_id_fkey;
    END IF;

    ALTER TABLE public.complaints
    ADD CONSTRAINT complaints_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES public.profiles(id)
    ON DELETE CASCADE;
END $$;

-- 5. Complaint Votes -> Complaints & Profiles
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'complaint_votes_complaint_id_fkey' AND table_name = 'complaint_votes'
    ) THEN
        ALTER TABLE public.complaint_votes DROP CONSTRAINT complaint_votes_complaint_id_fkey;
    END IF;

    ALTER TABLE public.complaint_votes
    ADD CONSTRAINT complaint_votes_complaint_id_fkey
    FOREIGN KEY (complaint_id)
    REFERENCES public.complaints(id)
    ON DELETE CASCADE;

    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'complaint_votes_user_id_fkey' AND table_name = 'complaint_votes'
    ) THEN
        ALTER TABLE public.complaint_votes DROP CONSTRAINT complaint_votes_user_id_fkey;
    END IF;

    ALTER TABLE public.complaint_votes
    ADD CONSTRAINT complaint_votes_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES public.profiles(id)
    ON DELETE CASCADE;
END $$;

-- 6. User Notifications -> Notices & Profiles
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'user_notifications_notice_id_fkey' AND table_name = 'user_notifications'
    ) THEN
        ALTER TABLE public.user_notifications DROP CONSTRAINT user_notifications_notice_id_fkey;
    END IF;

    ALTER TABLE public.user_notifications
    ADD CONSTRAINT user_notifications_notice_id_fkey
    FOREIGN KEY (notice_id)
    REFERENCES public.notices(id)
    ON DELETE CASCADE;

    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints 
        WHERE constraint_name = 'user_notifications_user_id_fkey' AND table_name = 'user_notifications'
    ) THEN
        ALTER TABLE public.user_notifications DROP CONSTRAINT user_notifications_user_id_fkey;
    END IF;

    ALTER TABLE public.user_notifications
    ADD CONSTRAINT user_notifications_user_id_fkey
    FOREIGN KEY (user_id)
    REFERENCES public.profiles(id)
    ON DELETE CASCADE;
END $$;
