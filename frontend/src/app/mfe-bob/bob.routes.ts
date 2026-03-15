import { Routes } from '@angular/router';

export const bobRoutes: Routes = [
    {
        path: 'template',
        children: [
            {
                path: '',
                loadComponent: () =>
                    import('../pages/training-template/training-template').then((m) => m.TrainingTemplateComponent),
            },
            {
                path: 'crm-mastery',
                loadComponent: () =>
                    import('../pages/training-template/training-crm-mastery/training-crm-mastery').then((m) => m.TrainingCrmMasteryComponent),
            },
        ],
    },
];
