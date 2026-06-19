import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { Observable } from 'rxjs';
import { sendInboxEmail } from '../../../../store/inbox/inbox.actions';
import { selectInboxSendError, selectInboxSending } from '../../../../store/inbox/inbox.selectors';

@Component({
  selector: 'app-email-compose',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './email-compose.html',
  styleUrl: './email-compose.css',
})
export class EmailComposeComponent {
    @Output() close = new EventEmitter<void>();
    @Output() emailSent = new EventEmitter<void>();

    composeForm: FormGroup;
    isSending$: Observable<boolean>;
    errorMsg$: Observable<string | null>;

    constructor(private fb: FormBuilder, private store: Store) {
        this.isSending$ = this.store.select(selectInboxSending);
        this.errorMsg$ = this.store.select(selectInboxSendError);

        this.composeForm = this.fb.group({
            to: ['', [Validators.required]],
            cc: [''],
            subject: ['', Validators.required],
            body: ['']
        });
    }

    sendEmail() {
        if (this.composeForm.invalid) {
            this.composeForm.markAllAsTouched();
            return;
        }

        const formValue = this.composeForm.value;

        // Simple split by comma for multiple recipients
        const toRecipients = formValue.to.split(',').map((e: string) => e.trim()).filter((e: string) => e);
        const ccRecipients = formValue.cc ? formValue.cc.split(',').map((e: string) => e.trim()).filter((e: string) => e) : [];

        this.store.dispatch(sendInboxEmail({ request: {
            subject: formValue.subject,
            body_content: formValue.body,
            to_recipients: toRecipients,
            cc_recipients: ccRecipients.length > 0 ? ccRecipients : undefined,
            body_type: 'html' // Use HTML by default even for simple text to allow future rich text
        } }));
        this.emailSent.emit();
        this.closeModal();
    }

    closeModal() {
        this.close.emit();
    }
}
