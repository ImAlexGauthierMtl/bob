// MS365 model — mirrors backend MS365 Pydantic schemas

export interface MS365Connection {
    id: string;
    userId: string;
    msEmail: string | null;
    isActive: boolean;
    lastEmailSync: string | null;
    lastCalendarSync: string | null;
    createdAt: string;
    updatedAt: string;
}

export interface MS365AuthUrl {
    authUrl: string;
}

export interface SyncedEmail {
    id: string;
    userId: string;
    msMessageId: string;
    subject: string | null;
    bodyPreview: string | null;
    bodyHtml: string | null;
    fromAddress: string | null;
    fromName: string | null;
    toAddresses: EmailAddress[] | null;
    ccAddresses: EmailAddress[] | null;
    receivedAt: string | null;
    isRead: boolean;
    importance: string;
    hasAttachments: boolean;
    attachmentsMeta: AttachmentMeta[] | null;
    folder: string;
    conversationId: string | null;
    linkedContactId: string | null;
    linkedOrganizationId: string | null;
    createdAt: string;
    updatedAt: string;
}

export interface SyncedEvent {
    id: string;
    userId: string;
    msEventId: string;
    subject: string | null;
    bodyHtml: string | null;
    location: string | null;
    startTime: string | null;
    endTime: string | null;
    isAllDay: boolean;
    organizerEmail: string | null;
    organizerName: string | null;
    attendees: Attendee[] | null;
    status: string;
    isCancelled: boolean;
    recurrence: Record<string, unknown> | null;
    onlineMeetingUrl: string | null;
    linkedContactId: string | null;
    linkedOrganizationId: string | null;
    createdAt: string;
    updatedAt: string;
}

export interface EmailAddress {
    address: string;
    name: string;
}

export interface AttachmentMeta {
    name: string;
    size: number;
    contentType: string;
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
    emailsSynced: number;
    eventsSynced: number;
    status: string;
}
