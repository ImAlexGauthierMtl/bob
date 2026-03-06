import { Routes } from '@angular/router';

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
                path: '',
                redirectTo: 'dashboard',
                pathMatch: 'full',
            },
        ],
    },
];
