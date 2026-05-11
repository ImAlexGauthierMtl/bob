import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { UserService } from '../../../shared/services/user.service';
import { User, CreateUserDto } from '../../../shared/models/user.model';

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

    // Add user dialog state
    showAddDialog = false;
    isCreating = false;
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    // Form fields
    newUserEmail = '';
    newUserPassword = '';
    newUserFirstName = '';
    newUserLastName = '';
    newUserRole = 'member';
    newUserJobTitle = '';
    newUserPhone = '';

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

    private userService = inject(UserService);

    ngOnInit(): void {
        this.loadUsers();
    }

    loadUsers(): void {
        this.isLoading = true;
        this.userService.getAll().subscribe({
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

        this.userService.update(this.selectedUser.id, { role: this.selectedRole }).subscribe({
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
        this.userService.update(user.id, {}).subscribe({
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

        this.userService.delete(user.id).subscribe({
            next: () => this.loadUsers(),
            error: (err) => {
                alert(err?.error?.detail || 'Failed to deactivate user.');
            },
        });
    }

    // ── Add User Dialog ─────────────────────────

    openAddDialog(): void {
        this.showAddDialog = true;
        this.resetForm();
    }

    closeAddDialog(): void {
        this.showAddDialog = false;
    }

    resetForm(): void {
        this.newUserEmail = '';
        this.newUserPassword = '';
        this.newUserFirstName = '';
        this.newUserLastName = '';
        this.newUserRole = 'member';
        this.newUserJobTitle = '';
        this.newUserPhone = '';
        this.isCreating = false;
        this.statusMessage = '';
    }

    get isFormValid(): boolean {
        return !!(
            this.newUserEmail.trim() &&
            this.newUserPassword.trim().length >= 8 &&
            this.newUserFirstName.trim() &&
            this.newUserLastName.trim()
        );
    }

    createUser(): void {
        if (!this.isFormValid) return;
        this.isCreating = true;
        this.statusMessage = '';

        const data: CreateUserDto = {
            email: this.newUserEmail.trim(),
            password: this.newUserPassword,
            first_name: this.newUserFirstName.trim(),
            last_name: this.newUserLastName.trim(),
            role: this.newUserRole,
            job_title: this.newUserJobTitle.trim() || undefined,
            phone: this.newUserPhone.trim() || undefined,
        };

        this.userService.create(data).subscribe({
            next: () => {
                this.statusMessage = '✅ User created successfully';
                this.statusType = 'success';
                this.loadUsers();
                setTimeout(() => this.closeAddDialog(), 1000);
            },
            error: (err) => {
                this.isCreating = false;
                this.statusMessage = err?.error?.detail || '❌ Failed to create user.';
                this.statusType = 'error';
            },
        });
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
