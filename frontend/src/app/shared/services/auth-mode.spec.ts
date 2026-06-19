import { describe, expect, it } from 'vitest';

import { shouldUseLocalCredentialLogin } from './auth-mode';

describe('local credential auth mode', () => {
    it('enables credential login only for explicit non-production local auth', () => {
        expect(shouldUseLocalCredentialLogin({ production: false, localAuthEnabled: true })).toBe(true);
        expect(shouldUseLocalCredentialLogin({ production: false, localAuthEnabled: false })).toBe(false);
        expect(shouldUseLocalCredentialLogin({ production: true, localAuthEnabled: true })).toBe(false);
        expect(shouldUseLocalCredentialLogin({ production: true, localAuthEnabled: false })).toBe(false);
    });
});
