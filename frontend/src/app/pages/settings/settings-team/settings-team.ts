import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UserService, User, UserCreateRequest } from '../../../shared/services/user.service';

@Component({
    selector: 'croo-settings-team',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './settings-team.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsTeamComponent implements OnInit {
    users: User[] = [];
    total = 0;
    isLoading = true;

    // Dialog state
    showAddDialog = false;
    userInput = '';
    isProcessing = false;
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    // Parsed preview
    parsedPreview: Partial<UserCreateRequest> | null = null;

    // Search
    searchQuery = '';

    // Dropdown menu
    activeMenuUserId: string | null = null;

    // Role dialog
    showRoleDialog = false;
    selectedUser: User | null = null;
    selectedRole = '';
    isSavingRole = false;
    roleStatusMessage = '';
    roleStatusType: 'info' | 'success' | 'error' = 'info';

    roleOptions = [
        { value: 'admin', label: 'Admin', icon: 'fa-solid fa-crown', desc: 'Full access — manage team, billing, and all settings' },
        { value: 'manager', label: 'Manager', icon: 'fa-solid fa-user-tie', desc: 'Can manage team members and view analytics' },
        { value: 'member', label: 'Member', icon: 'fa-solid fa-user', desc: 'Standard access — create and edit own records' },
        { value: 'readonly', label: 'Read Only', icon: 'fa-solid fa-eye', desc: 'View-only access — cannot create or modify data' },
    ];

    constructor(private userService: UserService) { }

    ngOnInit(): void {
        this.loadUsers();
    }

    loadUsers(): void {
        this.isLoading = true;
        this.userService.listUsers().subscribe({
            next: (res) => {
                this.users = res.items;
                this.total = res.total;
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
    }

    // ── Dropdown Menu ────────────────────────────

    openUserMenu(user: User, event: Event): void {
        event.stopPropagation();
        this.activeMenuUserId = this.activeMenuUserId === user.id ? null : user.id;
    }

    closeAllMenus(): void {
        this.activeMenuUserId = null;
    }

    // ── Role Dialog ─────────────────────────────

    openRoleDialog(user: User): void {
        this.selectedUser = user;
        this.selectedRole = user.role;
        this.showRoleDialog = true;
        this.roleStatusMessage = '';
        this.activeMenuUserId = null;
    }

    closeRoleDialog(): void {
        this.showRoleDialog = false;
        this.selectedUser = null;
    }

    saveRole(): void {
        if (!this.selectedUser || this.selectedRole === this.selectedUser.role) return;
        this.isSavingRole = true;
        this.roleStatusMessage = '';

        this.userService.updateUser(this.selectedUser.id, { role: this.selectedRole }).subscribe({
            next: () => {
                this.isSavingRole = false;
                this.roleStatusMessage = '✅ Role updated successfully';
                this.roleStatusType = 'success';
                this.loadUsers();
                setTimeout(() => this.closeRoleDialog(), 1000);
            },
            error: (err) => {
                this.isSavingRole = false;
                this.roleStatusMessage = err?.error?.detail || '❌ Failed to update role';
                this.roleStatusType = 'error';
            },
        });
    }

    // ── Admin Actions ───────────────────────────

    resetUserPassword(user: User): void {
        this.activeMenuUserId = null;
        const tempPassword = this.generateTempPassword();
        this.userService.updateUser(user.id, {}).subscribe({
            next: () => {
                alert(`Password reset link would be sent to ${user.email}.\nTemp password: ${tempPassword}`);
            },
            error: () => {
                alert('Failed to reset password.');
            },
        });
    }

    deactivateUser(user: User): void {
        this.activeMenuUserId = null;
        if (!confirm(`Are you sure you want to deactivate ${user.first_name} ${user.last_name}?`)) return;

        this.userService.deleteUser(user.id).subscribe({
            next: () => this.loadUsers(),
            error: (err) => {
                alert(err?.error?.detail || 'Failed to deactivate user.');
            },
        });
    }

    // ── Add User Dialog ─────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.resetDialog();
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    resetDialog(): void {
        this.userInput = '';
        this.isProcessing = false;
        this.isCreating = false;
        this.statusMessage = '';
        this.parsedPreview = null;
    }

    // ── Bob Agent Processing ─────────────────

    processInput(): void {
        if (!this.userInput.trim()) return;
        this.isProcessing = true;
        this.statusMessage = '';
        this.parsedPreview = null;

        setTimeout(() => {
            this.parsedPreview = this.parseUserText(this.userInput);
            this.isProcessing = false;
        }, 600);
    }

    createFromParsed(): void {
        if (!this.parsedPreview?.first_name || !this.parsedPreview?.last_name || !this.parsedPreview?.email) return;
        this.isCreating = true;

        const data: UserCreateRequest = {
            email: this.parsedPreview.email,
            password: this.generateTempPassword(),
            first_name: this.parsedPreview.first_name,
            last_name: this.parsedPreview.last_name,
            role: this.parsedPreview.role || 'member',
            job_title: this.parsedPreview.job_title,
            phone: this.parsedPreview.phone,
        };

        this.userService.createUser(data).subscribe({
            next: () => {
                this.showAddDialog = false;
                this.loadUsers();
            },
            error: (err) => {
                this.isCreating = false;
                this.statusMessage = err?.error?.detail || '❌ Failed to create user.';
                this.statusType = 'error';
            },
        });
    }

    /**
     * Smart text parser — extracts user fields from free-form text.
     */
    private parseUserText(text: string): Partial<UserCreateRequest> {
        const result: Partial<UserCreateRequest> = {};

        const emailMatch = text.match(/[\w.+-]+@[\w.-]+\.\w{2,}/);
        if (emailMatch) {
            result.email = emailMatch[0];
            text = text.replace(emailMatch[0], '');
        }

        const phoneMatch = text.match(/(?:\+?1?\s*)?(?:\(?\d{3}\)?[\s.-]?)?\d{3}[\s.-]?\d{4}/);
        if (phoneMatch) {
            result.phone = phoneMatch[0].trim();
            text = text.replace(phoneMatch[0], '');
        }

        text = text.replace(/[,;|·•—–-]+/g, ' ').replace(/\s+/g, ' ').trim();

        const roleMap: Record<string, string> = {
            admin: 'admin',
            manager: 'manager',
            'sales rep': 'sales_rep',
            sales: 'sales_rep',
            support: 'support',
            member: 'member',
        };
        const roleLower = text.toLowerCase();
        for (const [keyword, role] of Object.entries(roleMap)) {
            if (roleLower.includes(keyword)) {
                result.role = role;
                text = text.replace(new RegExp(keyword, 'i'), '').trim();
                break;
            }
        }

        const titleKeywords = /\b(CEO|CTO|CFO|COO|CMO|CIO|VP|Director|Manager|Engineer|Developer|Designer|Analyst|Coordinator|Specialist|Lead|Head|Chief|Senior|Junior|Sr\.|Jr\.|President|Founder|Partner|Associate|Consultant|Advisor|Officer)\b/i;

        const words = text.split(' ').filter(w => w.length > 0);
        let titleStartIdx = -1;
        for (let i = 0; i < words.length; i++) {
            if (titleKeywords.test(words[i])) {
                titleStartIdx = i;
                break;
            }
        }

        if (titleStartIdx >= 0) {
            const namePart = words.slice(0, titleStartIdx).join(' ').trim();
            const titlePart = words.slice(titleStartIdx).join(' ').trim();
            if (namePart) {
                const nameParts = namePart.split(' ');
                result.first_name = nameParts[0];
                result.last_name = nameParts.slice(1).join(' ') || 'Unknown';
            }
            if (titlePart) {
                result.job_title = titlePart;
            }
        } else {
            const cleanedWords = words.filter(w => !(/^\d+$/.test(w)));
            if (cleanedWords.length >= 2) {
                result.first_name = cleanedWords[0];
                result.last_name = cleanedWords.slice(1).join(' ');
            } else if (cleanedWords.length === 1) {
                result.first_name = cleanedWords[0];
                result.last_name = 'Unknown';
            }
        }

        return result;
    }

    private generateTempPassword(): string {
        return 'Temp' + Math.random().toString(36).slice(2, 10) + '!1';
    }

    // ── Helpers ──────────────────────────────

    getInitials(u: User): string {
        return `${u.first_name[0]}${u.last_name[0]}`.toUpperCase();
    }

    getRoleBadgeClass(role: string): string {
        switch (role) {
            case 'admin': return 'status-badge--purple';
            case 'manager': return 'status-badge--blue';
            case 'sales_rep': return 'status-badge--green';
            case 'support': return 'status-badge--gray';
            default: return 'status-badge--gray';
        }
    }

    getRoleLabel(role: string): string {
        switch (role) {
            case 'admin': return 'Admin';
            case 'manager': return 'Manager';
            case 'sales_rep': return 'Sales Rep';
            case 'support': return 'Support';
            case 'readonly': return 'Read Only';
            default: return 'Member';
        }
    }

    get filteredUsers(): User[] {
        if (!this.searchQuery.trim()) return this.users;
        const q = this.searchQuery.toLowerCase();
        return this.users.filter(u =>
            u.first_name.toLowerCase().includes(q) ||
            u.last_name.toLowerCase().includes(q) ||
            u.email.toLowerCase().includes(q)
        );
    }
}
