import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { EmailService } from '../../../../shared/services/email.service';
import { finalize } from 'rxjs';

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
    isSending = false;
    errorMsg = '';

    constructor(private fb: FormBuilder, private emailService: EmailService) {
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

        this.isSending = true;
        this.errorMsg = '';
        const formValue = this.composeForm.value;

        // Simple split by comma for multiple recipients
        const toRecipients = formValue.to.split(',').map((e: string) => e.trim()).filter((e: string) => e);
        const ccRecipients = formValue.cc ? formValue.cc.split(',').map((e: string) => e.trim()).filter((e: string) => e) : [];

        this.emailService.sendEmail({
            subject: formValue.subject,
            body_content: formValue.body,
            to_recipients: toRecipients,
            cc_recipients: ccRecipients.length > 0 ? ccRecipients : undefined,
            body_type: 'html' // Use HTML by default even for simple text to allow future rich text
        }).pipe(
            finalize(() => {
                this.isSending = false;
            })
        ).subscribe({
            next: () => {
                this.emailSent.emit();
                this.closeModal();
            },
            error: (err) => {
                this.errorMsg = 'Failed to send email. Please try again.';
                console.error('Error sending email:', err);
            }
        });
    }

    closeModal() {
        this.close.emit();
    }
}
