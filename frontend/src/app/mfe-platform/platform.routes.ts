import { Routes } from '@angular/router';

export const platformRoutes: Routes = [
    {
        path: 'dashboard',
        loadComponent: () =>
            import('../pages/dashboard/dashboard').then((m) => m.DashboardComponent),
    },
    {
        path: 'analytics',
        loadComponent: () =>
            import('../pages/analytics/analytics').then((m) => m.AnalyticsComponent),
    },
    {
        path: 'tenants',
        loadComponent: () =>
            import('../pages/tenants/tenants').then((m) => m.TenantsComponent),
    },
    {
        path: 'tenants/:id',
        loadComponent: () =>
            import('../pages/tenant-detail/tenant-detail').then((m) => m.TenantDetailComponent),
    },
    {
        path: 'usage-logs',
        loadComponent: () =>
            import('../pages/usage-logs/usage-logs').then((m) => m.UsageLogsComponent),
    },
    {
        path: 'knowledge-base',
        loadComponent: () =>
            import('../pages/knowledge-base/kb-portal').then((m) => m.KBPortalComponent),
    },
    {
        path: 'knowledge-base/:slug',
        loadComponent: () =>
            import('../pages/knowledge-base/kb-article').then((m) => m.KBArticleComponent),
    },
];
