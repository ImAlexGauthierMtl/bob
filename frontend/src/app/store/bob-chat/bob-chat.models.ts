import { BobChannel } from '../../shared/models/bob.model';
import { BobAction } from '../../shared/services/bob-action.service';

export interface BobChatToolStep {
    tool: string;
    status: string;
}

export interface BobChatArtifactFieldView {
    label: string;
    value: string;
}

export interface BobChatArtifactLinkView {
    label: string;
    url: string;
    icon?: string;
}

export interface BobChatArtifactItemView {
    label: string;
    value: string;
    change?: string;
    icon?: string;
    percent?: number;
    time?: string;
    description?: string;
}

export interface BobChatArtifactSectionView {
    title: string;
    subtitle?: string;
    badge?: string;
    items: BobChatArtifactItemView[];
}

export interface BobChatArtifactView {
    type: string;
    title: string;
    fields: BobChatArtifactFieldView[];
    status: 'building' | 'complete' | 'partial';
    entityId?: string;
    links?: BobChatArtifactLinkView[];
    columns?: string[];
    rows?: string[][];
    items?: BobChatArtifactItemView[];
    sections?: BobChatArtifactSectionView[];
}

export interface BobChatMessageView {
    id: string;
    role: 'user' | 'bob';
    text: string;
    time: Date;
    isLoading?: boolean;
    toolSteps?: BobChatToolStep[];
    artifact?: BobChatArtifactView;
}

export interface BobChatSessionSummary {
    id: string;
    title: string;
    turnCount: number;
    createdAt: Date;
    updatedAt: Date;
}

export interface BobChatSessionGroup {
    label: string;
    sessions: BobChatSessionSummary[];
}

export interface BobChatMissionState {
    prompt?: string;
    context?: Record<string, unknown>;
    active: boolean;
}

export interface BobChatSendSuccessPayload {
    responseMessage: BobChatMessageView;
    sessionId: string;
    sessionTitle: string;
    actions: BobAction[];
}

export interface BobChatSendRequest {
    messageId: string;
    loadingMessageId: string;
    text: string;
    channel: BobChannel;
}
