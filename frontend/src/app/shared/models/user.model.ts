// User model — mirrors backend UserResponse Pydantic schema

export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    job_title: string | null;
    phone: string | null;
    bio: string | null;
    location: string | null;
    timezone: string | null;
    role: string;
    created_at: string;
    updated_at: string;
}

export interface UserListResponse {
    items: User[];
    total: number;
    skip: number;
    limit: number;
}

export interface CreateUserDto {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
    role?: string;
    job_title?: string;
    phone?: string;
}

export interface UpdateUserDto {
    first_name?: string;
    last_name?: string;
    job_title?: string;
    phone?: string;
    bio?: string;
    location?: string;
    timezone?: string;
    role?: string;
}
