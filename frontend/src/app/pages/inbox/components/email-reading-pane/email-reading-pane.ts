import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { SyncedEmail, EmailAiInsightResponse } from '../../../../shared/models/ms365.model';
import { MS365Service } from '../../../../shared/services/ms365.service';
import { catchError, finalize } from 'rxjs/operators';
import { of } from 'rxjs';

@Component({
    selector: 'app-email-reading-pane',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule],
    templateUrl: './email-reading-pane.html',
    styleUrl: './email-reading-pane.css'
})
export class EmailReadingPaneComponent implements OnChanges {
    @Input() email: SyncedEmail | null = null;
    
    replyForm: FormGroup;
    isReplying = false;
    replyError: string | null = null;

    forwardForm: FormGroup;
    isForwarding = false;
    forwardError: string | null = null;

    activeTab: 'reply' | 'forward' = 'reply';
    sanitizedBodyHtml: SafeHtml | null = null;

    constructor(private ms365Service: MS365Service, private fb: FormBuilder, private sanitizer: DomSanitizer) {
        this.replyForm = this.fb.group({
            comment: ['', Validators.required]
        });
        
        this.forwardForm = this.fb.group({
            to_recipients: ['', Validators.required],
            comment: ['']
        });
    }

    ngOnChanges(changes: SimpleChanges): void {
        if (changes['email'] && this.email) {
            this.replyError = null;
            this.forwardError = null;
            this.replyForm.reset();
            this.forwardForm.reset();
            this.activeTab = 'reply';
            this.sanitizedBodyHtml = this.email.body_html
                ? this.sanitizer.bypassSecurityTrustHtml(this.email.body_html)
                : null;
        } else if (!this.email) {
            this.replyError = null;
            this.forwardError = null;
            this.replyForm.reset();
            this.forwardForm.reset();
            this.sanitizedBodyHtml = null;
        }
    }

    get hasSelection(): boolean {
        return !!this.email;
    }

    sendReply(): void {
        if (!this.email || this.replyForm.invalid || this.isReplying) return;

        this.isReplying = true;
        this.replyError = null;
        const comment = this.replyForm.get('comment')?.value;

        this.ms365Service.replyEmail(this.email.id, { comment, reply_all: false })
            .pipe(
                finalize(() => this.isReplying = false)
            )
            .subscribe({
                next: () => {
                    this.replyForm.reset();
                    // Optionally trigger a toast or update local thread
                },
                error: (err) => {
                    console.error('Failed to reply', err);
                    this.replyError = 'Failed to send reply.';
                }
            });
    }

    sendForward(): void {
        if (!this.email || this.forwardForm.invalid || this.isForwarding) return;

        this.isForwarding = true;
        this.forwardError = null;
        const formValues = this.forwardForm.value;
        
        // Simple split by comma/semicolon for multiple recipients
        const to_recipients = formValues.to_recipients
            .split(/[,;]+/)
            .map((email: string) => email.trim())
            .filter((email: string) => email.length > 0);

        if (to_recipients.length === 0) {
            this.forwardError = 'Please provide at least one valid recipient.';
            this.isForwarding = false;
            return;
        }

        this.ms365Service.forwardEmail(this.email.id, { 
            to_recipients, 
            comment: formValues.comment || '' 
        })
            .pipe(
                finalize(() => this.isForwarding = false)
            )
            .subscribe({
                next: () => {
                    this.forwardForm.reset();
                    // Optionally show success message
                },
                error: (err) => {
                    console.error('Failed to forward', err);
                    this.forwardError = 'Failed to send forward message.';
                }
            });
    }

    setActiveTab(tab: 'reply' | 'forward'): void {
        this.activeTab = tab;
    }

    parseSmartLabel(label: string): string[] {
        if (!label) return [];
        return label.split(' > ').map(p => p.trim());
    }
}

