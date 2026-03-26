// MS365 model — mirrors backend MS365 Pydantic schemas

export interface MS365Connection {
    id: string;
    user_id: string;
    ms_email: string | null;
    is_active: boolean;
    connection_status: 'active' | 'token_expired' | 'needs_reauth' | string;
    last_email_sync: string | null;
    last_calendar_sync: string | null;
    created_at: string;
    updated_at: string;
}

export interface MS365AuthUrl {
    auth_url: string;
}

export interface SyncedEmail {
    id: string;
    user_id: string;
    ms_message_id: string;
    subject: string | null;
    body_preview: string | null;
    body_html: string | null;
    from_address: string | null;
    from_name: string | null;
    to_addresses: EmailAddress[] | null;
    cc_addresses: EmailAddress[] | null;
    received_at: string | null;
    is_read: boolean;
    importance: string;
    has_attachments: boolean;
    attachments_meta: AttachmentMeta[] | null;
    folder: string;
    conversation_id: string | null;
    linked_contact_id: string | null;
    linked_organization_id: string | null;
    smart_label?: string | null;
    ai_summary?: string | null;
    ai_action_items?: string[] | null;
    created_at: string;
    updated_at: string;
}

export interface SyncedEvent {
    id: string;
    user_id: string;
    ms_event_id: string;
    subject: string | null;
    body_html: string | null;
    location: string | null;
    start_time: string | null;
    end_time: string | null;
    is_all_day: boolean;
    organizer_email: string | null;
    organizer_name: string | null;
    attendees: Attendee[] | null;
    status: string;
    is_cancelled: boolean;
    recurrence: Record<string, unknown> | null;
    online_meeting_url: string | null;
    linked_contact_id: string | null;
    linked_organization_id: string | null;
    created_at: string;
    updated_at: string;
}

export interface EmailAddress {
    address: string;
    name: string;
}

export interface AttachmentMeta {
    name: string;
    size: number;
    content_type: string;
}

export interface Attendee {
    email: string;
    name: string;
    status: string;
}

export interface SyncedEmailListResponse {
    items: SyncedEmail[];
    total: number;
    skip: number;
    limit: number;
}

export interface SyncedEventListResponse {
    items: SyncedEvent[];
    total: number;
    skip: number;
    limit: number;
}

export interface SyncStatus {
    emails_synced: number;
    events_synced: number;
    status: string;
}

export interface EmailAiInsightResponse {
    summary: string;
    smart_label: string;
    action_items: string[];
}

export interface SendEmailRequest {
    subject: string;
    body_content: string;
    to_recipients: string[];
    cc_recipients?: string[];
    bcc_recipients?: string[];
    body_type?: string;
}

export interface ReplyEmailRequest {
    comment: string;
    reply_all?: boolean;
}

export interface ForwardEmailRequest {
    to_recipients: string[];
    comment?: string;
}
