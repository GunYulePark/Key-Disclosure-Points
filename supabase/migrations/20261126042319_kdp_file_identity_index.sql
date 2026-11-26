-- Cover the complete immutable-file foreign key reported by hosted advisors.
-- Preserve the existing shorter index until usage evidence supports removal.
create index kdp_files_version_identity_idx on public.kdp_document_files
  (workspace_id, document_version_id, sha256, byte_length);
