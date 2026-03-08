import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RoleService, Role, Permission } from '../../../shared/services/role.service';

@Component({
    selector: 'croo-settings-roles',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './settings-roles.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsRolesComponent implements OnInit {
    roles: Role[] = [];
    permissions: Permission[] = [];
    isLoading = true;

    // Create dialog
    showCreateDialog = false;
    newRoleName = '';
    newRoleDescription = '';
    isCreating = false;

    // Edit dialog
    showEditDialog = false;
    editingRole: Role | null = null;
    editName = '';
    editDescription = '';
    isSavingEdit = false;

    // Permission dialog
    showPermDialog = false;
    permRole: Role | null = null;
    selectedPermIds: Set<string> = new Set();
    isSavingPerms = false;

    // Status
    statusMessage = '';
    statusType: 'info' | 'success' | 'error' = 'info';

    constructor(private roleService: RoleService) { }

    ngOnInit(): void {
        this.loadData();
    }

    loadData(): void {
        this.isLoading = true;
        this.roleService.listRoles().subscribe({
            next: (res) => {
                this.roles = res.items;
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
        this.roleService.listPermissions().subscribe({
            next: (perms) => (this.permissions = perms),
        });
    }

    // ── Helpers ──────────────────────────────────

    get groupedPermissions(): { resource: string; perms: Permission[] }[] {
        const map = new Map<string, Permission[]>();
        for (const p of this.permissions) {
            if (!map.has(p.resource)) map.set(p.resource, []);
            map.get(p.resource)!.push(p);
        }
        return Array.from(map.entries())
            .map(([resource, perms]) => ({ resource, perms }))
            .sort((a, b) => a.resource.localeCompare(b.resource));
    }

    getRolePermCount(role: Role): number {
        return role.permissions?.length || 0;
    }

    getRoleIcon(role: Role): string {
        if (role.is_system) return 'fa-solid fa-lock';
        return 'fa-solid fa-shield-halved';
    }

    getRoleBadgeClass(role: Role): string {
        if (role.is_system) return 'status-badge--purple';
        return 'status-badge--blue';
    }

    capitalizeResource(resource: string): string {
        return resource.charAt(0).toUpperCase() + resource.slice(1);
    }

    // ── Create Role ─────────────────────────────

    openCreateDialog(): void {
        this.newRoleName = '';
        this.newRoleDescription = '';
        this.showCreateDialog = true;
        this.statusMessage = '';
    }

    closeCreateDialog(): void {
        this.showCreateDialog = false;
    }

    createRole(): void {
        if (!this.newRoleName.trim()) return;
        this.isCreating = true;

        this.roleService.createRole({
            name: this.newRoleName.trim(),
            description: this.newRoleDescription.trim() || undefined,
        }).subscribe({
            next: () => {
                this.isCreating = false;
                this.showCreateDialog = false;
                this.loadData();
            },
            error: (err) => {
                this.isCreating = false;
                this.statusMessage = err?.error?.detail || 'Failed to create role';
                this.statusType = 'error';
            },
        });
    }

    // ── Edit Role ───────────────────────────────

    openEditDialog(role: Role): void {
        this.editingRole = role;
        this.editName = role.name;
        this.editDescription = role.description || '';
        this.showEditDialog = true;
        this.statusMessage = '';
    }

    closeEditDialog(): void {
        this.showEditDialog = false;
        this.editingRole = null;
    }

    saveEdit(): void {
        if (!this.editingRole || !this.editName.trim()) return;
        this.isSavingEdit = true;

        this.roleService.updateRole(this.editingRole.id, {
            name: this.editName.trim(),
            description: this.editDescription.trim() || undefined,
        }).subscribe({
            next: () => {
                this.isSavingEdit = false;
                this.showEditDialog = false;
                this.loadData();
            },
            error: (err) => {
                this.isSavingEdit = false;
                this.statusMessage = err?.error?.detail || 'Failed to update role';
                this.statusType = 'error';
            },
        });
    }

    // ── Delete Role ─────────────────────────────

    deleteRole(role: Role): void {
        if (role.is_system) return;
        if (!confirm(`Delete role "${role.name}"? Users assigned this role will lose these permissions.`)) return;

        this.roleService.deleteRole(role.id).subscribe({
            next: () => this.loadData(),
            error: (err) => {
                alert(err?.error?.detail || 'Failed to delete role');
            },
        });
    }

    // ── Permissions Management ──────────────────

    openPermDialog(role: Role): void {
        this.permRole = role;
        this.selectedPermIds = new Set(role.permissions.map(p => p.id));
        this.showPermDialog = true;
        this.statusMessage = '';
    }

    closePermDialog(): void {
        this.showPermDialog = false;
        this.permRole = null;
    }

    togglePerm(permId: string): void {
        if (this.selectedPermIds.has(permId)) {
            this.selectedPermIds.delete(permId);
        } else {
            this.selectedPermIds.add(permId);
        }
    }

    toggleAllPermsForResource(resource: string): void {
        const group = this.permissions.filter(p => p.resource === resource);
        const allSelected = group.every(p => this.selectedPermIds.has(p.id));
        for (const p of group) {
            if (allSelected) {
                this.selectedPermIds.delete(p.id);
            } else {
                this.selectedPermIds.add(p.id);
            }
        }
    }

    isResourceFullySelected(resource: string): boolean {
        return this.permissions
            .filter(p => p.resource === resource)
            .every(p => this.selectedPermIds.has(p.id));
    }

    savePermissions(): void {
        if (!this.permRole) return;
        this.isSavingPerms = true;

        this.roleService.setRolePermissions(
            this.permRole.id,
            Array.from(this.selectedPermIds),
        ).subscribe({
            next: () => {
                this.isSavingPerms = false;
                this.showPermDialog = false;
                this.loadData();
            },
            error: (err) => {
                this.isSavingPerms = false;
                this.statusMessage = err?.error?.detail || 'Failed to update permissions';
                this.statusType = 'error';
            },
        });
    }
}
