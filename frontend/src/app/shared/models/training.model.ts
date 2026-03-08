// Training model — mirrors backend Training Pydantic schemas

export interface TrainingSession {
    id: string;
    user_id: string;
    training_slug: string;
    current_slide: number;
    started_at: string;
}

export interface TrainingNote {
    id: string;
    session_id: string;
    slide_id: number | null;
    content: string;
    note_type: 'insight' | 'action' | 'important';
    created_at: string;
}

export interface TrainingMissing {
    id: string;
    session_id: string;
    label: string;
    category: 'integration' | 'feature' | 'process';
    description: string | null;
    created_at: string;
}
