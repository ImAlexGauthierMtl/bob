import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { catchError, of, switchMap, throwError } from 'rxjs';
import { MS365Service } from '../../../shared/services/ms365.service';
import { MembraneService } from '../../../shared/services/membrane.service';
import { MembraneBackendService, MembraneBackendConnection, MembraneBackendEmail, MembraneBackendEvent } from '../../../shared/services/membrane-backend.service';
import { AuthService } from '../../../shared/services/auth.service';
import { MS365Connection, SyncedEmail, SyncedEvent } from '../../../shared/models/ms365.model';

type UnifiedEmail = SyncedEmail | MembraneBackendEmail;
type UnifiedEvent = SyncedEvent | MembraneBackendEvent;

function isMembraneEmail(e: UnifiedEmail): e is MembraneBackendEmail {
    return 'provider_message_id' in e;
}

function isMembraneEvent(e: UnifiedEvent): e is MembraneBackendEvent {
    return 'provider_event_id' in e;
}

@Component({
    selector: 'croo-settings-ms365',
    standalone: true,
    imports: [CommonModule, RouterLink],
    templateUrl: './settings-ms365.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsMs365Component implements OnInit {
    private ms365Service = inject(MS365Service);
    private membraneService = inject(MembraneService);
    private membraneBackend = inject(MembraneBackendService);
    private authService = inject(AuthService);

    // Legacy MS365 state
    connection: MS365Connection | null = null;
    // Membrane state
    membraneConnection: MembraneBackendConnection | null = null;
    userId: string = '';

    emails: UnifiedEmail[] = [];
    events: UnifiedEvent[] = [];
    activeTab: 'emails' | 'calendar' = 'emails';
    syncing = false;
    loading = true;
    emailTotal = 0;
    eventTotal = 0;

    get isConnected(): boolean {
        return !!this.connection?.is_active || !!this.membraneConnection?.is_active;
    }

    get connectedEmail(): string | null {
        return this.connection?.ms_email || this.membraneConnection?.connection_name || null;
    }

    get lastEmailSync(): string | null {
        return this.connection?.last_email_sync || this.membraneConnection?.last_email_sync || null;
    }

    get lastCalendarSync(): string | null {
        return this.connection?.last_calendar_sync || this.membraneConnection?.last_calendar_sync || null;
    }

    get provider(): 'legacy' | 'membrane' | null {
        if (this.connection?.is_active) return 'legacy';
        if (this.membraneConnection?.is_active) return 'membrane';
        return null;
    }

    ngOnInit(): void {
        this.authService.user$.subscribe((user) => {
            if (user?.id) {
                this.userId = user.id;
                this.loadData();
            }
        });
    }

    loadData(): void {
        this.loading = true;
        this.loadConnection();
    }

    loadConnection(): void {
        this.ms365Service.getConnection().subscribe({
            next: (conn) => {
                this.connection = conn;
                if (conn?.is_active) {
                    this.loading = false;
                    this.loadEmails();
                    this.loadEvents();
                } else {
                    this.tryLoadMembraneConnection();
                }
            },
            error: () => {
                this.connection = null;
                this.tryLoadMembraneConnection();
            },
        });
    }

    tryLoadMembraneConnection(): void {
        if (!this.userId) {
            this.loading = false;
            return;
        }
        this.membraneBackend.getConnection(this.userId, 'microsoft-outlook').subscribe({
            next: (conn) => {
                this.membraneConnection = conn;
                this.loading = false;
                if (conn?.is_active) {
                    this.loadMembraneEmails();
                    this.loadMembraneEvents();
                }
            },
            error: () => {
                this.membraneConnection = null;
                this.loading = false;
            },
        });
    }

    loadEmails(): void {
        this.ms365Service.getEmails(0, 20).subscribe({
            next: (res) => {
                this.emails = res.items;
                this.emailTotal = res.total;
            },
        });
    }

    loadEvents(): void {
        this.ms365Service.getEvents(0, 20).subscribe({
            next: (res) => {
                this.events = res.items;
                this.eventTotal = res.total;
            },
        });
    }

    loadMembraneEmails(): void {
        this.membraneBackend.getEmails(this.userId, 0, 20).subscribe({
            next: (res) => {
                this.emails = res.items;
                this.emailTotal = res.total;
            },
        });
    }

    loadMembraneEvents(): void {
        this.membraneBackend.getEvents(this.userId, 0, 20).subscribe({
            next: (res) => {
                this.events = res.items;
                this.eventTotal = res.total;
            },
        });
    }

    forceSync(): void {
        if (this.provider === 'legacy') {
            this.syncing = true;
            this.ms365Service.triggerSync().subscribe({
                next: () => {
                    this.syncing = false;
                    this.loadConnection();
                },
                error: () => { this.syncing = false; },
            });
        } else if (this.provider === 'membrane') {
            // Trigger a Membrane action (e.g. 'microsoft-outlook.sync-emails')
            this.syncing = true;
            this.membraneBackend.runAction('microsoft-outlook.sync-emails', {}).subscribe({
                next: () => {
                    this.syncing = false;
                    this.loadMembraneEmails();
                    this.loadMembraneEvents();
                },
                error: () => { this.syncing = false; },
            });
        }
    }

    setTab(tab: 'emails' | 'calendar'): void {
        this.activeTab = tab;
    }

    formatDate(iso: string | null): string {
        if (!iso) return '—';
        return new Date(iso).toLocaleString();
    }

    /** Display subject from either legacy or Membrane email. */
    emailSubject(email: UnifiedEmail): string {
        if (isMembraneEmail(email)) {
            return email.subject || '(No subject)';
        }
        return email.subject || '(No subject)';
    }

    /** Display sender from either legacy or Membrane email. */
    emailFrom(email: UnifiedEmail): string {
        if (isMembraneEmail(email)) {
            return email.from_name || email.from_address || 'Unknown';
        }
        return email.from_name || email.from_address || 'Unknown';
    }

    /** Display received_at from either legacy or Membrane email. */
    emailReceivedAt(email: UnifiedEmail): string | null {
        if (isMembraneEmail(email)) {
            return email.received_at;
        }
        return email.received_at;
    }

    /** Display body preview from either legacy or Membrane email. */
    emailBodyPreview(email: UnifiedEmail): string | null {
        if (isMembraneEmail(email)) {
            return email.body_preview;
        }
        return email.body_preview;
    }

    /** Display unread dot from either legacy or Membrane email. */
    emailIsRead(email: UnifiedEmail): boolean {
        if (isMembraneEmail(email)) {
            return email.is_read;
        }
        return email.is_read;
    }

    /** Display attachments indicator from either legacy or Membrane email. */
    emailHasAttachments(email: UnifiedEmail): boolean {
        if (isMembraneEmail(email)) {
            return email.has_attachments;
        }
        return email.has_attachments;
    }

    /** Display event subject from either legacy or Membrane event. */
    eventSubject(event: UnifiedEvent): string {
        if (isMembraneEvent(event)) {
            return event.subject || '(No title)';
        }
        return event.subject || '(No title)';
    }

    /** Display event start time from either legacy or Membrane event. */
    eventStartTime(event: UnifiedEvent): string | null {
        if (isMembraneEvent(event)) {
            return event.start_time;
        }
        return event.start_time;
    }

    /** Display event end time from either legacy or Membrane event. */
    eventEndTime(event: UnifiedEvent): string | null {
        if (isMembraneEvent(event)) {
            return event.end_time;
        }
        return event.end_time;
    }

    /** Display event location from either legacy or Membrane event. */
    eventLocation(event: UnifiedEvent): string | null {
        if (isMembraneEvent(event)) {
            return event.location;
        }
        return event.location;
    }

    /** Display event cancelled status from either legacy or Membrane event. */
    eventIsCancelled(event: UnifiedEvent): boolean {
        if (isMembraneEvent(event)) {
            return event.is_cancelled;
        }
        return event.is_cancelled;
    }

    /** Display online meeting URL from either legacy or Membrane event. */
    eventOnlineMeetingUrl(event: UnifiedEvent): string | null {
        if (isMembraneEvent(event)) {
            return event.online_meeting_url;
        }
        return event.online_meeting_url;
    }

    disconnect(): void {
        if (!confirm('Disconnect Microsoft Outlook?')) return;

        if (this.provider === 'legacy' && this.connection) {
            this.ms365Service.disconnect().subscribe({
                next: () => {
                    this.connection = null;
                },
            });
        } else if (this.provider === 'membrane' && this.membraneConnection) {
            const connection = this.membraneConnection;
            this.membraneService.disconnect(connection.membrane_connection_id, connection.integration_key).pipe(
                catchError((err) => err?.status === 404 ? of(undefined) : throwError(() => err)),
                switchMap(() => this.membraneBackend.disconnectConnection(connection.id)),
                catchError((err) => {
                    console.error('Failed to disconnect Pipedream Outlook connection', err);
                    alert('Failed to disconnect. Please try again.');
                    return throwError(() => err);
                }),
            ).subscribe({
                next: () => {
                    this.membraneConnection = null;
                    this.emails = [];
                    this.events = [];
                    this.emailTotal = 0;
                    this.eventTotal = 0;
                },
            });
        }
    }
}
