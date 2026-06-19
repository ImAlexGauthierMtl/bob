export type AuthEnvironment = {
    production: boolean;
    localAuthEnabled?: boolean;
};

export function shouldUseLocalCredentialLogin(config: AuthEnvironment): boolean {
    return !config.production && config.localAuthEnabled === true;
}
