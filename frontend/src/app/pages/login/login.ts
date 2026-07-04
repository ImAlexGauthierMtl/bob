import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../shared/services/auth.service';

@Component({
    selector: 'croo-login',
    standalone: true,
    imports: [FormsModule],
    templateUrl: './login.html',
    styleUrl: './login.css',
})
export class LoginComponent {
    passwordVisible = false;
    rememberMe = false;
    email = '';
    password = '';
    errorMessage = '';
    isLoading = false;

    constructor(
        private authService: AuthService,
        private router: Router,
    ) {
        this.authService.ensureSession().subscribe({
            next: (session) => {
                if (session.authenticated) {
                    this.router.navigate(['/dashboard']);
                }
            },
            error: () => {
                // Stay on the login screen until local credentials or Bob Cloud provide a session.
            },
        });
    }

    togglePasswordVisibility(): void {
        this.passwordVisible = !this.passwordVisible;
    }

    onSubmit(event: Event): void {
        event.preventDefault();
        const credentials = this.getSubmittedCredentials(event);
        this.email = credentials.email;
        this.password = credentials.password;
        this.errorMessage = '';
        this.isLoading = true;

        this.authService
            .login(credentials)
            .subscribe({
                next: () => {
                    this.router.navigate(['/dashboard']);
                },
                error: (err) => {
                    this.isLoading = false;
                    if (err.status === 401) {
                        this.errorMessage = 'Email ou mot de passe invalide.';
                    } else if (err.status === 429) {
                        this.errorMessage = 'Too many attempts. Please wait.';
                    } else {
                        this.errorMessage = 'Connexion locale indisponible. Please try again.';
                    }
                },
            });
    }

    private getSubmittedCredentials(event: Event): { email: string; password: string } {
        const form = event.currentTarget instanceof HTMLFormElement ? event.currentTarget : null;
        if (!form) {
            return { email: this.email.trim(), password: this.password };
        }

        const formData = new FormData(form);
        const submittedEmail = formData.get('email');
        const submittedPassword = formData.get('password');

        return {
            email: typeof submittedEmail === 'string' ? submittedEmail.trim() : this.email.trim(),
            password: typeof submittedPassword === 'string' ? submittedPassword : this.password,
        };
    }

}
