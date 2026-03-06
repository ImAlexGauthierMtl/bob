import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UserService, User, UserUpdateRequest } from '../../../shared/services/user.service';

@Component({
    selector: 'croo-settings-profile',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './settings-profile.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsProfileComponent implements OnInit {
    isLoading = true;
    isSaving = false;
    saveMessage = '';
    saveType: 'success' | 'error' = 'success';

    // Form model
    firstName = '';
    lastName = '';
    email = '';
    jobTitle = '';
    phone = '';
    bio = '';
    location = '';
    timezone = 'America/Montreal';

    constructor(private userService: UserService) { }

    ngOnInit(): void {
        this.loadProfile();
    }

    loadProfile(): void {
        this.isLoading = true;
        this.userService.getMe().subscribe({
            next: (user: User) => {
                this.firstName = user.first_name;
                this.lastName = user.last_name;
                this.email = user.email;
                this.jobTitle = user.job_title || '';
                this.phone = user.phone || '';
                this.bio = user.bio || '';
                this.location = user.location || '';
                this.timezone = user.timezone || 'America/Montreal';
                this.isLoading = false;
            },
            error: () => {
                this.isLoading = false;
            },
        });
    }

    saveProfile(): void {
        this.isSaving = true;
        this.saveMessage = '';

        const data: UserUpdateRequest = {
            first_name: this.firstName,
            last_name: this.lastName,
            job_title: this.jobTitle || undefined,
            phone: this.phone || undefined,
            bio: this.bio || undefined,
            location: this.location || undefined,
            timezone: this.timezone || undefined,
        };

        this.userService.updateMe(data).subscribe({
            next: () => {
                this.isSaving = false;
                this.saveMessage = 'Profile updated successfully';
                this.saveType = 'success';
                setTimeout(() => (this.saveMessage = ''), 3000);
            },
            error: () => {
                this.isSaving = false;
                this.saveMessage = 'Failed to update profile';
                this.saveType = 'error';
            },
        });
    }

    getInitials(): string {
        return `${this.firstName[0] || ''}${this.lastName[0] || ''}`.toUpperCase();
    }
}
