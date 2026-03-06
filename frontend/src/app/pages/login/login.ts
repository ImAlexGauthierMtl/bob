import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';

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

    togglePasswordVisibility(): void {
        this.passwordVisible = !this.passwordVisible;
    }

    onSubmit(event: Event): void {
        event.preventDefault();
        // TODO: Implement authentication logic
    }

    signInWithGoogle(): void {
        // TODO: Implement Google SSO
    }

    signInWithMicrosoft(): void {
        // TODO: Implement Microsoft SSO
    }

    signInWithBiometric(): void {
        // TODO: Implement biometric authentication
    }
}
