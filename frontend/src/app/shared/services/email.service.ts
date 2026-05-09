import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of, throwError } from 'rxjs';
import { catchError, filter, map, switchMap, take } from 'rxjs/operators';
import { MS365Service } from './ms365.service';
import { MembraneBackendService, MembraneBackendConnection, MembraneBackendEmail } from './membrane-backend.service';
import { AuthService } from './auth.service';
import {
    UnifiedConnection,
    UnifiedEmail,
    UnifiedEmailListResponse,
    isMembraneEmail
} from '../models/unified-email.model';
import { MS365Connection, SyncedEmail, SyncedEmailListResponse, SendEmailRequest, ReplyEmailRequest, ForwardEmailRequest } from '../models/ms365.model';

@Injectable({ providedIn: 'root' })
export class EmailService {
    private ms365Service = inject(MS365Service);
    private membraneService = inject(MembraneBackendService);
    private authService = inject(AuthService);

    private getUserId(): Observable<string> {
        return this.authService.user$.pipe(
            filter(u => !!u),
            take(1),
            map(u => u.id)
        );
    }

    /** Try Membrane connection, fallback to legacy */
    getConnection(): Observable<UnifiedConnection | null> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.getConnection(userId).pipe(
                map(mConn => this.mapMembraneConnection(mConn)),
                catchError(() => this.ms365Service.getConnection().pipe(
                    map(conn => conn && conn.is_active ? this.mapLegacyConnection(conn) : null),
                    catchError(() => of(null))
                ))
            )),
            catchError(() => this.ms365Service.getConnection().pipe(
                map(conn => conn && conn.is_active ? this.mapLegacyConnection(conn) : null),
                catchError(() => of(null))
            ))
        );
    }

    /** Try Membrane emails, fallback to legacy */
    getEmails(skip = 0, limit = 50, folder?: string, search?: string, smartLabel?: string, linkedContactId?: string): Observable<UnifiedEmailListResponse> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.getEmails(userId, skip, limit, folder, search, smartLabel, linkedContactId).pipe(
                map(res => this.mapMembraneEmailList(res)),
                catchError(() => this.ms365Service.getEmails(skip, limit, folder, search, smartLabel, linkedContactId).pipe(
                    map(res => this.mapLegacyEmailList(res)),
                    catchError(err => {
                        console.error('EmailService: both membrane and legacy email fetch failed', err);
                        return throwError(() => err);
                    })
                ))
            )),
            catchError(err => {
                console.error('EmailService: membrane email fetch failed, trying legacy', err);
                return this.ms365Service.getEmails(skip, limit, folder, search, smartLabel, linkedContactId).pipe(
                    map(res => this.mapLegacyEmailList(res)),
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy email fetch failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    /** Try Membrane getEmail, fallback to legacy */
    getEmail(id: string): Observable<UnifiedEmail> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.getEmail(id, userId).pipe(
                map(e => this.mapMembraneEmail(e)),
                catchError(() => this.ms365Service.getEmail(id).pipe(
                    map(e => this.mapLegacyEmail(e)),
                    catchError(err => {
                        console.error('EmailService: both membrane and legacy getEmail failed', err);
                        return throwError(() => err);
                    })
                ))
            )),
            catchError(err => {
                return this.ms365Service.getEmail(id).pipe(
                    map(e => this.mapLegacyEmail(e)),
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy getEmail failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    /** Try Membrane send, fallback to legacy */
    sendEmail(request: SendEmailRequest): Observable<{ status: string }> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.sendEmail(userId, request).pipe(
                catchError(() => this.ms365Service.sendEmail(request).pipe(
                    catchError(err => {
                        console.error('EmailService: both membrane and legacy send failed', err);
                        return throwError(() => err);
                    })
                ))
            )),
            catchError(err => {
                return this.ms365Service.sendEmail(request).pipe(
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy send failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    /** Try Membrane reply, fallback to legacy */
    replyEmail(id: string, request: ReplyEmailRequest): Observable<{ status: string }> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.replyEmail(id, userId, request).pipe(
                catchError(() => this.ms365Service.replyEmail(id, request).pipe(
                    catchError(err => {
                        console.error('EmailService: both membrane and legacy reply failed', err);
                        return throwError(() => err);
                    })
                ))
            )),
            catchError(err => {
                return this.ms365Service.replyEmail(id, request).pipe(
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy reply failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    /** Try Membrane forward, fallback to legacy */
    forwardEmail(id: string, request: ForwardEmailRequest): Observable<{ status: string }> {
        return this.getUserId().pipe(
            switchMap(userId => this.membraneService.forwardEmail(id, userId, request).pipe(
                catchError(() => this.ms365Service.forwardEmail(id, request).pipe(
                    catchError(err => {
                        console.error('EmailService: both membrane and legacy forward failed', err);
                        return throwError(() => err);
                    })
                ))
            )),
            catchError(err => {
                return this.ms365Service.forwardEmail(id, request).pipe(
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy forward failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    /** Trigger sync — pull latest emails via Membrane proxy first, fallback to legacy MS365 */
    triggerSync(): Observable<any> {
        return this.membraneService.syncEmails(50).pipe(
            catchError(err => {
                console.warn('EmailService: membrane sync failed, trying legacy', err);
                return this.ms365Service.triggerSync().pipe(
                    catchError(err2 => {
                        console.error('EmailService: both membrane and legacy sync failed', err2);
                        return throwError(() => err2);
                    })
                );
            })
        );
    }

    // Mappers
    private mapLegacyConnection(c: MS365Connection): UnifiedConnection {
        return {
            id: c.id,
            email: c.ms_email,
            isActive: c.is_active,
            status: c.connection_status,
            lastEmailSync: c.last_email_sync,
            source: 'legacy'
        };
    }

    private mapMembraneConnection(c: MembraneBackendConnection): UnifiedConnection {
        return {
            id: c.id,
            email: c.connection_name,
            isActive: c.is_active,
            status: c.is_active ? 'active' : 'inactive',
            lastEmailSync: c.last_email_sync,
            source: 'membrane'
        };
    }

    private mapLegacyEmail(e: SyncedEmail): UnifiedEmail {
        return { ...e, source: 'legacy' } as UnifiedEmail;
    }

    private mapMembraneEmail(e: MembraneBackendEmail): UnifiedEmail {
        return {
            id: e.id,
            user_id: e.user_id,
            provider_message_id: e.provider_message_id,
            subject: e.subject,
            body_preview: e.body_preview,
            body_html: e.body_html,
            from_address: e.from_address,
            from_name: e.from_name,
            to_addresses: e.to_addresses,
            cc_addresses: e.cc_addresses,
            received_at: e.received_at,
            is_read: e.is_read,
            importance: e.importance,
            has_attachments: e.has_attachments,
            attachments_meta: e.attachments_meta,
            folder: e.folder,
            conversation_id: e.conversation_id,
            linked_contact_id: e.linked_contact_id,
            linked_organization_id: e.linked_organization_id,
            created_at: e.created_at,
            membrane_connection_id: e.membrane_connection_id,
            provider: e.provider,
            tenant_id: e.tenant_id,
        };
    }

    private mapLegacyEmailList(res: SyncedEmailListResponse): UnifiedEmailListResponse {
        return {
            items: res.items.map(e => this.mapLegacyEmail(e)),
            total: res.total,
            skip: res.skip,
            limit: res.limit
        };
    }

    private mapMembraneEmailList(res: { items: MembraneBackendEmail[]; total: number; skip: number; limit: number }): UnifiedEmailListResponse {
        return {
            items: res.items.map(e => this.mapMembraneEmail(e)),
            total: res.total,
            skip: res.skip,
            limit: res.limit
        };
    }
}
