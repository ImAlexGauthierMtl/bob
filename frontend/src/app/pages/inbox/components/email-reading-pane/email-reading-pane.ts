import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { UnifiedEmail } from '../../../../shared/models/unified-email.model';
import { forwardInboxEmail, replyInboxEmail } from '../../../../store/inbox/inbox.actions';
import {
    selectInboxForwardError,
    selectInboxForwarding,
    selectInboxReplyError,
    selectInboxReplying,
} from '../../../../store/inbox/inbox.selectors';

@Component({
    selector: 'app-email-reading-pane',
    standalone: true,
    imports: [CommonModule, ReactiveFormsModule],
    templateUrl: './email-reading-pane.html',
    styleUrl: './email-reading-pane.css'
})
export class EmailReadingPaneComponent implements OnChanges {
    @Input() email: UnifiedEmail | null = null;
    @Output() backRequested = new EventEmitter<void>();
    @Output() emailActionCompleted = new EventEmitter<void>();
    
    replyForm: FormGroup;
    isReplying$: Observable<boolean>;
    replyError$: Observable<string | null>;

    forwardForm: FormGroup;
    isForwarding$: Observable<boolean>;
    forwardError$: Observable<string | null>;

    activeTab: 'reply' | 'forward' = 'reply';
    sanitizedBodyHtml: SafeHtml | null = null;

    constructor(private store: Store, private fb: FormBuilder, private sanitizer: DomSanitizer) {
        this.isReplying$ = this.store.select(selectInboxReplying);
        this.replyError$ = this.store.select(selectInboxReplyError);
        this.isForwarding$ = this.store.select(selectInboxForwarding);
        this.forwardError$ = this.store.select(selectInboxForwardError);

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
            this.replyForm.reset();
            this.forwardForm.reset();
            this.activeTab = 'reply';
            this.sanitizedBodyHtml = this.email.body_html
                ? this.sanitizer.bypassSecurityTrustHtml(this.email.body_html)
                : null;
        } else if (!this.email) {
            this.replyForm.reset();
            this.forwardForm.reset();
            this.sanitizedBodyHtml = null;
        }
    }

    get hasSelection(): boolean {
        return !!this.email;
    }

    sendReply(): void {
        if (!this.email || this.replyForm.invalid) return;
        const comment = this.replyForm.get('comment')?.value;

        this.store.dispatch(replyInboxEmail({ id: this.email.id, request: { comment, reply_all: false } }));
        this.replyForm.reset();
        this.emailActionCompleted.emit();
    }

    sendForward(): void {
        if (!this.email || this.forwardForm.invalid) return;
        const formValues = this.forwardForm.value;
        
        // Simple split by comma/semicolon for multiple recipients
        const to_recipients = formValues.to_recipients
            .split(/[,;]+/)
            .map((email: string) => email.trim())
            .filter((email: string) => email.length > 0);

        if (to_recipients.length === 0) {
            return;
        }

        this.store.dispatch(forwardInboxEmail({
            id: this.email.id,
            request: {
                to_recipients,
                comment: formValues.comment || ''
            }
        }));
        this.forwardForm.reset();
        this.emailActionCompleted.emit();
    }

    setActiveTab(tab: 'reply' | 'forward'): void {
        this.activeTab = tab;
    }

    goBack(): void {
        this.backRequested.emit();
    }

    parseSmartLabel(label: string): string[] {
        if (!label) return [];
        return label.split(' > ').map(p => p.trim());
    }
}
