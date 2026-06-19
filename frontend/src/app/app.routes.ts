import { Routes } from '@angular/router';
import { authGuard } from './shared/guards/auth.guard';

export const routes: Routes = [
    {
        path: 'login',
        loadComponent: () =>
            import('./pages/login/login').then((m) => m.LoginComponent),
    },
    {
        path: 'select-organization',
        loadComponent: () =>
            import('./pages/org-selector/org-selector').then((m) => m.OrgSelectorComponent),
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
                path: 'inbox',
                loadComponent: () =>
                    import('./pages/inbox/inbox-overview').then(
                        (m) => m.InboxOverviewComponent
                    ),
            },
            {
                path: 'conversation',
                loadComponent: () =>
                    import('./pages/chat/chat').then(
                        (m) => m.ChatComponent
                    ),
            },
            {
                path: 'chat',
                redirectTo: 'conversation',
                pathMatch: 'full',
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
                path: 'tasks',
                loadComponent: () =>
                    import('./pages/activities/activities').then(
                        (m) => m.ActivitiesComponent
                    ),
            },
            {
                path: 'analytics',
                loadComponent: () =>
                    import('./pages/analytics/analytics').then(
                        (m) => m.AnalyticsComponent
                    ),
            },
            {
                path: 'tenants',
                loadComponent: () =>
                    import('./pages/tenants/tenants').then(
                        (m) => m.TenantsComponent
                    ),
            },
            {
                path: 'tenants/:id',
                loadComponent: () =>
                    import('./pages/tenant-detail/tenant-detail').then(
                        (m) => m.TenantDetailComponent
                    ),
            },
            {
                path: 'usage-logs',
                loadComponent: () =>
                    import('./pages/usage-logs/usage-logs').then(
                        (m) => m.UsageLogsComponent
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
                        path: 'ms365',
                        loadComponent: () =>
                            import('./pages/settings/settings-ms365/settings-ms365').then(
                                (m) => m.SettingsMs365Component
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
                        path: 'roles',
                        loadComponent: () =>
                            import('./pages/settings/settings-roles/settings-roles').then(
                                (m) => m.SettingsRolesComponent
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
                        path: 'automation/builder/:id',
                        loadComponent: () =>
                            import('./pages/settings/workflow-builder/workflow-builder').then(
                                (m) => m.WorkflowBuilderComponent
                            ),
                    },
                    {
                        path: 'bob/capabilities',
                        loadComponent: () =>
                            import('./pages/settings/bob-capabilities/bob-capabilities').then(
                                (m) => m.BobCapabilitiesComponent
                            ),
                    },
                    {
                        path: 'bob-control-center',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-control-center').then(
                                (m) => m.BccControlCenterComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:roleId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-role-detail/bcc-role-detail').then(
                                (m) => m.BccRoleDetailComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:orgId/departments/:deptId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-child-profile/bcc-child-profile').then(
                                (m) => m.BccChildProfileComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:orgId/teams/:teamId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-child-profile/bcc-child-profile').then(
                                (m) => m.BccChildProfileComponent
                            ),
                    },
                    {
                        path: 'inbox',
                        loadComponent: () =>
                            import('./pages/settings/settings-inbox/settings-inbox').then(
                                (m) => m.SettingsInboxComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:orgId/roles/:roleId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-role-view/bcc-role-view').then(
                                (m) => m.BccRoleViewComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:orgId/roles/:roleId/skills/:skillId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-skill-view/bcc-skill-view').then(
                                (m) => m.BccSkillViewComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/:orgId/roles/:roleId/tasks/:taskId',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-task-view/bcc-task-view').then(
                                (m) => m.BccTaskViewComponent
                            ),
                    },
                    {
                        path: 'bob-control-center/library/:type/:id',
                        loadComponent: () =>
                            import('./pages/settings/bcc-control-center/bcc-library-detail/bcc-library-detail').then(
                                (m) => m.BccLibraryDetailComponent
                            ),
                    },
                    {
                        path: 'products',
                        loadComponent: () =>
                            import('./pages/settings/settings-products/settings-products').then(
                                (m) => m.SettingsProductsComponent
                            ),
                    },
                    {
                        path: 'products/:id',
                        loadComponent: () =>
                            import('./pages/settings/settings-products/product-detail/product-detail').then(
                                (m) => m.ProductDetailComponent
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
                path: 'knowledge-base',
                loadComponent: () =>
                    import('./pages/knowledge-base/kb-portal').then(
                        (m) => m.KBPortalComponent
                    ),
            },
            {
                path: 'knowledge-base/:slug',
                loadComponent: () =>
                    import('./pages/knowledge-base/kb-article').then(
                        (m) => m.KBArticleComponent
                    ),
            },
            {
                path: 'template',
                children: [
                    {
                        path: '',
                        loadComponent: () =>
                            import('./pages/training-template/training-template').then(
                                (m) => m.TrainingTemplateComponent
                            ),
                    },
                    {
                        path: 'crm-mastery',
                        loadComponent: () =>
                            import('./pages/training-template/training-crm-mastery/training-crm-mastery').then(
                                (m) => m.TrainingCrmMasteryComponent
                            ),
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
