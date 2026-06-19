import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { ClientMap, GoldenNote, CreateGoldenNote, MeddpiccScoreDetail, BehavioralProfile } from '../models/client-map.model';

@Injectable({ providedIn: 'root' })
export class ClientMapService {
  private baseUrl = environment.agentControlApiUrl;

  constructor(private http: HttpClient) {}

  /** Get Client Map for a contact (returns 404 if not created yet) */
  getByContactId(contactId: string): Observable<ClientMap> {
    return this.http.get<ClientMap>(`${this.baseUrl}/contacts/${contactId}/client-map`);
  }

  /** Create or update the Client Map */
  upsert(contactId: string, data: Partial<ClientMap>): Observable<ClientMap> {
    return this.http.put<ClientMap>(`${this.baseUrl}/contacts/${contactId}/client-map`, data);
  }

  /** Add a Golden Note */
  addGoldenNote(contactId: string, note: CreateGoldenNote): Observable<GoldenNote> {
    return this.http.post<GoldenNote>(`${this.baseUrl}/contacts/${contactId}/client-map/golden-notes`, note);
  }

  /** Update a Golden Note */
  updateGoldenNote(contactId: string, noteId: string, data: Partial<CreateGoldenNote>): Observable<GoldenNote> {
    return this.http.put<GoldenNote>(`${this.baseUrl}/contacts/${contactId}/client-map/golden-notes/${noteId}`, data);
  }

  /** Delete a Golden Note */
  deleteGoldenNote(contactId: string, noteId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/contacts/${contactId}/client-map/golden-notes/${noteId}`);
  }

  /** Get detailed MEDDPICC score breakdown */
  getMeddpiccScore(contactId: string): Observable<MeddpiccScoreDetail> {
    return this.http.get<MeddpiccScoreDetail>(`${this.baseUrl}/contacts/${contactId}/client-map/meddpicc-score`);
  }

  /** Trigger AI behavioral analysis */
  analyzeBehavior(contactId: string): Observable<{ status: string; behavioral_profile: BehavioralProfile }> {
    return this.http.post<{ status: string; behavioral_profile: BehavioralProfile }>(
      `${this.baseUrl}/contacts/${contactId}/client-map/analyze-behavior`, {}
    );
  }
}
