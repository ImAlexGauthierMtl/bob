import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { TrainingSession, TrainingNote, TrainingMissing } from '../models/training.model';

const API_URL = `${environment.apiUrl}/training`;

@Injectable({ providedIn: 'root' })
export class TrainingService {
    private http = inject(HttpClient);

    createSession(slug: string): Observable<TrainingSession> {
        return this.http.post<TrainingSession>(`${API_URL}/sessions`, { training_slug: slug });
    }

    updateSlide(sessionId: string, slide: number): Observable<unknown> {
        return this.http.patch(`${API_URL}/sessions/${sessionId}/slide`, { current_slide: slide });
    }

    getNotes(sessionId: string): Observable<TrainingNote[]> {
        return this.http.get<TrainingNote[]>(`${API_URL}/sessions/${sessionId}/notes`);
    }

    createNote(sessionId: string, content: string, slideId?: number, noteType = 'insight'): Observable<TrainingNote> {
        return this.http.post<TrainingNote>(`${API_URL}/sessions/${sessionId}/notes`, {
            content,
            slide_id: slideId,
            note_type: noteType,
        });
    }

    deleteNote(noteId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/notes/${noteId}`);
    }

    getMissing(sessionId: string): Observable<TrainingMissing[]> {
        return this.http.get<TrainingMissing[]>(`${API_URL}/sessions/${sessionId}/missing`);
    }

    createMissing(sessionId: string, label: string, category = 'integration', description?: string): Observable<TrainingMissing> {
        return this.http.post<TrainingMissing>(`${API_URL}/sessions/${sessionId}/missing`, {
            label,
            category,
            description,
        });
    }

    deleteMissing(itemId: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/missing/${itemId}`);
    }
}
