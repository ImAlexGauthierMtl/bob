import { Routes } from '@angular/router';
import { authGuard } from './shared/guards/auth.guard';

export const routes: Routes = [
    {
        path: 'login',
        loadComponent: () =>
            import('./pages/login/login').then((m) => m.LoginComponent),
    },
    {
        path: '',
        loadComponent: () =>
            import('./shared/layout/layout').then((m) => m.LayoutComponent),
        canActivate: [authGuard],
        children: [
            {
                path: 'dashboard',
                loadComponent: () =>
                    import('./pages/dashboard/dashboard').then(
                        (m) => m.DashboardComponent
                    ),
            },
            {
                path: 'organizations',
                loadComponent: () =>
                    import('./pages/organizations/organizations').then(
                        (m) => m.OrganizationsComponent
                    ),
            },
            {
                path: 'organizations/:id',
                loadComponent: () =>
                    import('./pages/organization-detail/organization-detail').then(
                        (m) => m.OrganizationDetailComponent
                    ),
            },
            {
                path: 'contacts',
                loadComponent: () =>
                    import('./pages/contacts/contacts').then(
                        (m) => m.ContactsComponent
                    ),
            },
            {
                path: 'contacts/:id',
                loadComponent: () =>
                    import('./pages/contact-profile/contact-profile').then(
                        (m) => m.ContactProfileComponent
                    ),
            },
            {
                path: 'opportunities',
                loadComponent: () =>
                    import('./pages/opportunities/opportunities').then(
                        (m) => m.OpportunitiesComponent
                    ),
            },
            {
                path: 'opportunities/:id',
                loadComponent: () =>
                    import('./pages/opportunity-profile/opportunity-profile').then(
                        (m) => m.OpportunityProfileComponent
                    ),
            },
            {
                path: 'quotes',
                loadComponent: () =>
                    import('./pages/quotes/quotes').then(
                        (m) => m.QuotesComponent
                    ),
            },
            {
                path: 'quotes/:id',
                loadComponent: () =>
                    import('./pages/quote-profile/quote-profile').then(
                        (m) => m.QuoteProfileComponent
                    ),
            },
            {
                path: 'activities',
                loadComponent: () =>
                    import('./pages/activities/activities').then(
                        (m) => m.ActivitiesComponent
                    ),
            },
            {
                path: 'settings',
                loadComponent: () =>
                    import('./pages/settings/settings').then(
                        (m) => m.SettingsComponent
                    ),
                children: [
                    {
                        path: 'profile',
                        loadComponent: () =>
                            import('./pages/settings/settings-profile/settings-profile').then(
                                (m) => m.SettingsProfileComponent
                            ),
                    },
                    {
                        path: 'security',
                        loadComponent: () =>
                            import('./pages/settings/settings-security/settings-security').then(
                                (m) => m.SettingsSecurityComponent
                            ),
                    },
                    {
                        path: 'bob',
                        loadComponent: () =>
                            import('./pages/settings/settings-bob/settings-bob').then(
                                (m) => m.SettingsBobComponent
                            ),
                    },
                    {
                        path: 'notifications',
                        loadComponent: () =>
                            import('./pages/settings/settings-notifications/settings-notifications').then(
                                (m) => m.SettingsNotificationsComponent
                            ),
                    },
                    {
                        path: 'integrations',
                        loadComponent: () =>
                            import('./pages/settings/settings-integrations/settings-integrations').then(
                                (m) => m.SettingsIntegrationsComponent
                            ),
                    },
                    {
                        path: 'team',
                        loadComponent: () =>
                            import('./pages/settings/settings-team/settings-team').then(
                                (m) => m.SettingsTeamComponent
                            ),
                    },
                    {
                        path: 'automation',
                        loadComponent: () =>
                            import('./pages/settings/settings-automation/settings-automation').then(
                                (m) => m.SettingsAutomationComponent
                            ),
                    },
                    {
                        path: '',
                        redirectTo: 'profile',
                        pathMatch: 'full',
                    },
                ],
            },
            {
                path: '',
                redirectTo: 'dashboard',
                pathMatch: 'full',
            },
        ],
    },
];
