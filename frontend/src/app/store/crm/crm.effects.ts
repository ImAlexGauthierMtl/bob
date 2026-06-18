import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import { CrmB4fService } from '../../shared/services/crm-b4f.service';
import { errorMessage } from '../remote-state';
import {
    loadCrmActivities,
    loadCrmActivitiesFailure,
    loadCrmActivitiesSuccess,
    loadCrmContacts,
    loadCrmContactsFailure,
    loadCrmContactsSuccess,
    loadCrmDashboard,
    loadCrmDashboardFailure,
    loadCrmDashboardSuccess,
    loadCrmOpportunities,
    loadCrmOpportunitiesFailure,
    loadCrmOpportunitiesSuccess,
    loadCrmOrganizations,
    loadCrmOrganizationsFailure,
    loadCrmOrganizationsSuccess,
} from './crm.actions';

@Injectable()
export class CrmEffects {
    private actions$ = inject(Actions);
    private crm = inject(CrmB4fService);

    loadDashboard$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCrmDashboard),
            switchMap(() =>
                this.crm.getDashboardSummary().pipe(
                    map((data) => loadCrmDashboardSuccess({ data })),
                    catchError((error) => of(loadCrmDashboardFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadOrganizations$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCrmOrganizations),
            switchMap((query) =>
                this.crm.getOrganizations(query).pipe(
                    map((data) => loadCrmOrganizationsSuccess({ data })),
                    catchError((error) => of(loadCrmOrganizationsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadContacts$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCrmContacts),
            switchMap((query) =>
                this.crm.getContacts(query).pipe(
                    map((data) => loadCrmContactsSuccess({ data })),
                    catchError((error) => of(loadCrmContactsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadOpportunities$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCrmOpportunities),
            switchMap((query) =>
                this.crm.getOpportunities(query).pipe(
                    map((data) => loadCrmOpportunitiesSuccess({ data })),
                    catchError((error) => of(loadCrmOpportunitiesFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadActivities$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCrmActivities),
            switchMap((query) =>
                this.crm.getActivities(query).pipe(
                    map((data) => loadCrmActivitiesSuccess({ data })),
                    catchError((error) => of(loadCrmActivitiesFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
