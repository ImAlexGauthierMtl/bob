import { Routes } from '@angular/router';

export const settingsRoutes: Routes = [
    {
        path: '',
        loadComponent: () =>
            import('../pages/settings/settings').then((m) => m.SettingsComponent),
        children: [
            {
                path: 'profile',
                loadComponent: () =>
                    import('../pages/settings/settings-profile/settings-profile').then((m) => m.SettingsProfileComponent),
            },
            {
                path: 'security',
                loadComponent: () =>
                    import('../pages/settings/settings-security/settings-security').then((m) => m.SettingsSecurityComponent),
            },
            {
                path: 'bob',
                loadComponent: () =>
                    import('../pages/settings/settings-bob/settings-bob').then((m) => m.SettingsBobComponent),
            },
            {
                path: 'notifications',
                loadComponent: () =>
                    import('../pages/settings/settings-notifications/settings-notifications').then((m) => m.SettingsNotificationsComponent),
            },
            {
                path: 'integrations',
                loadComponent: () =>
                    import('../pages/settings/settings-integrations/settings-integrations').then((m) => m.SettingsIntegrationsComponent),
            },
            {
                path: 'ms365',
                loadComponent: () =>
                    import('../pages/settings/settings-ms365/settings-ms365').then((m) => m.SettingsMs365Component),
            },
            {
                path: 'team',
                loadComponent: () =>
                    import('../pages/settings/settings-team/settings-team').then((m) => m.SettingsTeamComponent),
            },
            {
                path: 'roles',
                loadComponent: () =>
                    import('../pages/settings/settings-roles/settings-roles').then((m) => m.SettingsRolesComponent),
            },
            {
                path: 'platform-access',
                loadComponent: () =>
                    import('../pages/settings/settings-platform-access/settings-platform-access').then((m) => m.SettingsPlatformAccessComponent),
            },
            {
                path: 'automation',
                loadComponent: () =>
                    import('../pages/settings/settings-automation/settings-automation').then((m) => m.SettingsAutomationComponent),
            },
            {
                path: 'automation/builder/:id',
                loadComponent: () =>
                    import('../pages/settings/workflow-builder/workflow-builder').then((m) => m.WorkflowBuilderComponent),
            },
            {
                path: 'bob/capabilities',
                loadComponent: () =>
                    import('../pages/settings/bob-capabilities/bob-capabilities').then((m) => m.BobCapabilitiesComponent),
            },
            {
                path: 'bob-control-center',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-control-center').then((m) => m.BccControlCenterComponent),
            },
            {
                path: 'bob-control-center/:roleId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-role-detail/bcc-role-detail').then((m) => m.BccRoleDetailComponent),
            },
            {
                path: 'bob-control-center/:orgId/departments/:deptId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-child-profile/bcc-child-profile').then((m) => m.BccChildProfileComponent),
            },
            {
                path: 'bob-control-center/:orgId/teams/:teamId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-child-profile/bcc-child-profile').then((m) => m.BccChildProfileComponent),
            },
            {
                path: 'inbox',
                loadComponent: () =>
                    import('../pages/settings/settings-inbox/settings-inbox').then((m) => m.SettingsInboxComponent),
            },
            {
                path: 'bob-control-center/:orgId/roles/:roleId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-role-view/bcc-role-view').then((m) => m.BccRoleViewComponent),
            },
            {
                path: 'bob-control-center/:orgId/roles/:roleId/skills/:skillId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-skill-view/bcc-skill-view').then((m) => m.BccSkillViewComponent),
            },
            {
                path: 'bob-control-center/:orgId/roles/:roleId/tasks/:taskId',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-task-view/bcc-task-view').then((m) => m.BccTaskViewComponent),
            },
            {
                path: 'bob-control-center/library/:type/:id',
                loadComponent: () =>
                    import('../pages/settings/bcc-control-center/bcc-library-detail/bcc-library-detail').then((m) => m.BccLibraryDetailComponent),
            },
            {
                path: 'products',
                loadComponent: () =>
                    import('../pages/settings/settings-products/settings-products').then((m) => m.SettingsProductsComponent),
            },
            {
                path: 'products/:id',
                loadComponent: () =>
                    import('../pages/settings/settings-products/product-detail/product-detail').then((m) => m.ProductDetailComponent),
            },
            {
                path: '',
                redirectTo: 'profile',
                pathMatch: 'full',
            },
        ],
    },
];
