import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import { CommunicationB4fService } from '../../shared/services/communication-b4f.service';
import { errorMessage } from '../remote-state';
import { loadCommunicationOverview, loadCommunicationOverviewFailure, loadCommunicationOverviewSuccess } from './communication.actions';

@Injectable()
export class CommunicationEffects {
    private actions$ = inject(Actions);
    private communication = inject(CommunicationB4fService);

    loadOverview$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadCommunicationOverview),
            switchMap(() =>
                this.communication.getIntegrationOverview().pipe(
                    map((data) => loadCommunicationOverviewSuccess({ data })),
                    catchError((error) => of(loadCommunicationOverviewFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
