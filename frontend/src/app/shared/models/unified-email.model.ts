// Unified email model — abstracts legacy MS365 and Membrane backend emails

import { AttachmentMeta, EmailAddress } from './ms365.model';

export interface UnifiedConnection {
    id: string;
    email: string | null;
    isActive: boolean;
    status: string;
    lastEmailSync: string | null;
    source: 'legacy' | 'membrane';
}

export interface UnifiedEmail {
    id: string;
    user_id: string;
    provider_message_id?: string;
    ms_message_id?: string;
    subject: string | null;
    body_preview: string | null;
    body_html: string | null;
    from_address: string | null;
    from_name: string | null;
    to_addresses: EmailAddress[] | null;
    cc_addresses: EmailAddress[] | null;
    received_at: string | null;
    is_read: boolean;
    importance?: string;
    has_attachments: boolean;
    attachments_meta?: AttachmentMeta[] | null;
    folder: string;
    conversation_id: string | null;
    linked_contact_id: string | null;
    linked_organization_id: string | null;
    smart_label?: string | null;
    ai_summary?: string | null;
    ai_action_items?: string[] | null;
    created_at: string;
    updated_at?: string;
    // local integration fields
    membrane_connection_id?: string;
    provider?: string;
    tenant_id?: string;
}

export interface UnifiedEmailListResponse {
    items: UnifiedEmail[];
    total: number;
    skip: number;
    limit: number;
}

export function isMembraneEmail(e: UnifiedEmail): boolean {
    return !!e.provider_message_id && !e.ms_message_id;
}
