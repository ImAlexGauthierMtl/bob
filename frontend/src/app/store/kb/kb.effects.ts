import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { catchError, map, of, switchMap } from 'rxjs';
import { KbB4fService } from '../../shared/services/kb-b4f.service';
import { errorMessage } from '../remote-state';
import { loadKbHome, loadKbHomeFailure, loadKbHomeSuccess } from './kb.actions';

@Injectable()
export class KbEffects {
    private actions$ = inject(Actions);
    private kb = inject(KbB4fService);

    loadHome$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadKbHome),
            switchMap(() =>
                this.kb.getHome().pipe(
                    map((data) => loadKbHomeSuccess({ data })),
                    catchError((error) => of(loadKbHomeFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );
}
