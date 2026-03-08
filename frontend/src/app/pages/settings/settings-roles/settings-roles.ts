import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RoleService } from '../../../shared/services/role.service';
import { Role, Permission } from '../../../shared/models/role.model';

@Component({
    selector: 'croo-settings-roles',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './settings-roles.html',
    styleUrls: ['../settings-shared.css'],
})
export class SettingsRolesComponent implements OnInit {
    private roleService = inject(RoleService);

    roles: Role[] = [];
    permissions: Permission[] = [];
    loading = true;
    error = '';

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

    ngOnInit(): void {
        this.loadItems();
    }

    loadItems(): void {
        this.loading = true;
        this.error = '';
        this.roleService.getAll().subscribe({
            next: (res) => {
                this.roles = res.items;
                this.loading = false;
            },
            error: () => {
                this.error = 'Impossible de charger les rôles.';
                this.loading = false;
            },
        });
        this.roleService.getPermissions().subscribe({
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

    // ── Créer un rôle ───────────────────────────

    openCreateDialog(): void {
        this.newRoleName = '';
        this.newRoleDescription = '';
        this.showCreateDialog = true;
        this.statusMessage = '';
    }

    closeCreateDialog(): void {
        this.showCreateDialog = false;
    }

    createItem(): void {
        if (!this.newRoleName.trim()) return;
        this.isCreating = true;

        this.roleService.create({
            name: this.newRoleName.trim(),
            description: this.newRoleDescription.trim() || undefined,
        }).subscribe({
            next: () => {
                this.isCreating = false;
                this.showCreateDialog = false;
                this.loadItems();
            },
            error: (err) => {
                this.isCreating = false;
                this.statusMessage = err?.error?.detail || 'Échec de la création du rôle';
                this.statusType = 'error';
            },
        });
    }

    // ── Modifier un rôle ────────────────────────

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

        this.roleService.update(this.editingRole.id, {
            name: this.editName.trim(),
            description: this.editDescription.trim() || undefined,
        }).subscribe({
            next: () => {
                this.isSavingEdit = false;
                this.showEditDialog = false;
                this.loadItems();
            },
            error: (err) => {
                this.isSavingEdit = false;
                this.statusMessage = err?.error?.detail || 'Échec de la mise à jour';
                this.statusType = 'error';
            },
        });
    }

    // ── Supprimer un rôle ───────────────────────

    deleteItem(role: Role): void {
        if (role.is_system) return;
        if (!confirm(`Supprimer le rôle « ${role.name} » ? Les utilisateurs assignés perdront ces permissions.`)) return;

        this.roleService.delete(role.id).subscribe({
            next: () => this.loadItems(),
            error: (err) => {
                alert(err?.error?.detail || 'Échec de la suppression du rôle');
            },
        });
    }

    // ── Gestion des permissions ─────────────────

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

        this.roleService.setPermissions(
            this.permRole.id,
            Array.from(this.selectedPermIds),
        ).subscribe({
            next: () => {
                this.isSavingPerms = false;
                this.showPermDialog = false;
                this.loadItems();
            },
            error: (err) => {
                this.isSavingPerms = false;
                this.statusMessage = err?.error?.detail || 'Échec de la mise à jour des permissions';
                this.statusType = 'error';
            },
        });
    }
}
