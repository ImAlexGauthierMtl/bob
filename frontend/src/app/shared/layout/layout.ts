import { Component, OnInit } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { BobChatComponent } from '../bob-chat/bob-chat';
import { environment } from '../../../environments/environment';

interface CurrentUser {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    job_title: string | null;
    role: string;
    is_super_admin: boolean;
}

@Component({
    selector: 'croo-layout',
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive, BobChatComponent],
    templateUrl: './layout.html',
    styleUrl: './layout.css',
})
export class LayoutComponent implements OnInit {
    userName = '';
    userRole = '';
    isSuperAdmin = false;

    constructor(private http: HttpClient) { }

    ngOnInit(): void {
        this.http.get<CurrentUser>(`${environment.apiUrl}/auth/me`).subscribe({
            next: (user) => {
                this.userName = `${user.first_name} ${user.last_name}`;
                this.userRole = user.job_title || user.role;
                this.isSuperAdmin = user.is_super_admin;
            },
            error: () => {
                this.userName = 'User';
                this.userRole = '';
            },
        });
    }
}
