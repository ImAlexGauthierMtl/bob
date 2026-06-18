import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import { CrmB4fService } from '../../shared/services/crm-b4f.service';
import { errorMessage } from '../remote-state';
import { loadCrmDashboard, loadCrmDashboardFailure, loadCrmDashboardSuccess } from './crm.actions';

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
}
