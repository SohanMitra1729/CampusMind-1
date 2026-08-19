-- =============================================================================
-- Supabase Storage Configuration & RLS Policies for campus-documents
-- Run this in Supabase SQL Editor to guarantee read/write access on cloud
-- =============================================================================

-- 1. Ensure the campus-documents bucket exists and is marked public
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'campus-documents',
    'campus-documents',
    true,
    52428800, -- 50 MB
    ARRAY['application/pdf']::text[]
)
ON CONFLICT (id) DO UPDATE 
SET public = true, file_size_limit = 52428800;

-- 2. Storage Policies for campus-documents
DO $$
BEGIN
    -- Allow public read access to all documents
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'Public Access to campus-documents' AND tablename = 'objects'
    ) THEN
        CREATE POLICY "Public Access to campus-documents"
        ON storage.objects FOR SELECT
        USING (bucket_id = 'campus-documents');
    END IF;

    -- Allow insert access for service_role and authenticated users
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'Service/Auth Insert on campus-documents' AND tablename = 'objects'
    ) THEN
        CREATE POLICY "Service/Auth Insert on campus-documents"
        ON storage.objects FOR INSERT
        WITH CHECK (bucket_id = 'campus-documents');
    END IF;

    -- Allow delete access for service_role and authenticated users
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'Service/Auth Delete on campus-documents' AND tablename = 'objects'
    ) THEN
        CREATE POLICY "Service/Auth Delete on campus-documents"
        ON storage.objects FOR DELETE
        USING (bucket_id = 'campus-documents');
    END IF;

    -- Allow update access
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE policyname = 'Service/Auth Update on campus-documents' AND tablename = 'objects'
    ) THEN
        CREATE POLICY "Service/Auth Update on campus-documents"
        ON storage.objects FOR UPDATE
        USING (bucket_id = 'campus-documents');
    END IF;
END $$;
