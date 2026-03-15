import { Routes } from '@angular/router';

export const inboxRoutes: Routes = [
    {
        path: '',
        loadComponent: () =>
            import('../pages/inbox/inbox-overview').then((m) => m.InboxOverviewComponent),
    },
];
