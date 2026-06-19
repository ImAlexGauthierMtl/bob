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
        this.errorMessage = '';
        this.isLoading = true;

        this.authService
            .login({ email: this.email, password: this.password })
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

    signInWithGoogle(): void {
        // TODO: Implement Google SSO
    }

    signInWithMicrosoft(): void {
        // TODO: Implement Microsoft SSO
    }

    signInWithBiometric(): void {
        // TODO: Implement biometric auth
    }
}
