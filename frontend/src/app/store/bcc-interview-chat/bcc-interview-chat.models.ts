export interface BccInterviewChatMessage {
    id: string;
    role: 'user' | 'bob';
    text: string;
    time: Date;
    isLoading?: boolean;
}

export interface BccInterviewSpeechCue {
    id: string;
    text: string;
}
