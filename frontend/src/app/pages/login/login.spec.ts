import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of } from 'rxjs';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { AuthService } from '../../shared/services/auth.service';
import { LoginComponent } from './login';

describe('LoginComponent', () => {
    let fixture: ComponentFixture<LoginComponent>;
    let authService: {
        ensureSession: ReturnType<typeof vi.fn>;
        login: ReturnType<typeof vi.fn>;
    };
    let router: {
        navigate: ReturnType<typeof vi.fn>;
    };

    beforeEach(async () => {
        authService = {
            ensureSession: vi.fn().mockReturnValue(of({ authenticated: false })),
            login: vi.fn().mockReturnValue(of({ authenticated: true })),
        };
        router = {
            navigate: vi.fn(),
        };

        await TestBed.configureTestingModule({
            imports: [LoginComponent],
            providers: [
                { provide: AuthService, useValue: authService },
                { provide: Router, useValue: router },
            ],
        }).compileComponents();

        fixture = TestBed.createComponent(LoginComponent);
        await fixture.whenStable();
        fixture.detectChanges();
    });

    it('submits the visible browser field values even when ngModel has not synced them yet', () => {
        const component = fixture.componentInstance;
        const form = fixture.nativeElement.querySelector('#login-form') as HTMLFormElement;
        const email = fixture.nativeElement.querySelector('#email') as HTMLInputElement;
        const password = fixture.nativeElement.querySelector('#password') as HTMLInputElement;

        email.value = ' admin@croo.digital ';
        password.value = 'visible-password';
        component.email = '';
        component.password = '';

        form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));

        expect(authService.login).toHaveBeenCalledWith({
            email: 'admin@croo.digital',
            password: 'visible-password',
        });
        expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
    });
});
