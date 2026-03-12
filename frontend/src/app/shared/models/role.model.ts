// Modèle TypeScript — miroir exact du RoleResponse / PermissionResponse Pydantic

// Permission
export interface Permission {
    id: string;
    resource: string;
    action: string;
    description: string | null;
}

// Role
export interface Role {
    id: string;
    name: string;
    description: string | null;
    is_system: boolean;
    permissions: Permission[];
}

// DTOs
export interface CreateRoleDto {
    name: string;
    description?: string;
}

export type UpdateRoleDto = Partial<CreateRoleDto>;

// List response
export interface RoleListResponse {
    items: Role[];
    total: number;
}
