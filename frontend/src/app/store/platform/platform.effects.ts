import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import { PlatformB4fService } from '../../shared/services/platform-b4f.service';
import { errorMessage } from '../remote-state';
import { loadPlatformOverview, loadPlatformOverviewFailure, loadPlatformOverviewSuccess } from './platform.actions';

@Injectable()
export class PlatformEffects {
    private actions$ = inject(Actions);
    private platform = inject(PlatformB4fService);

    loadOverview$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadPlatformOverview),
            switchMap(() =>
                this.platform.getOverview().pipe(
                    map((data) => loadPlatformOverviewSuccess({ data })),
                    catchError((error) => of(loadPlatformOverviewFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
