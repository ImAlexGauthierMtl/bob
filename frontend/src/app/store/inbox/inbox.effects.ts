import { Injectable, inject } from '@angular/core';
import { Actions, createEffect, ofType } from '@ngrx/effects';
import { Store } from '@ngrx/store';
import { catchError, exhaustMap, filter, map, of, switchMap, withLatestFrom } from 'rxjs';
import { EmailService } from '../../shared/services/email.service';
import { SmartLabelService } from '../../shared/services/smart-label.service';
import { errorMessage } from '../remote-state';
import {
    forwardInboxEmail,
    forwardInboxEmailFailure,
    forwardInboxEmailSuccess,
    loadInboxConnection,
    loadInboxConnectionFailure,
    loadInboxConnectionSuccess,
    loadInboxEmails,
    loadInboxEmailsFailure,
    loadInboxEmailsSuccess,
    loadInboxLabels,
    loadInboxLabelsFailure,
    loadInboxLabelsSuccess,
    loadMoreInboxEmails,
    refreshInboxEmails,
    refreshInboxEmailsFailure,
    replyInboxEmail,
    replyInboxEmailFailure,
    replyInboxEmailSuccess,
    sendInboxEmail,
    sendInboxEmailFailure,
    sendInboxEmailSuccess,
    setInboxFilter,
} from './inbox.actions';
import { selectInboxFilter, selectInboxHasMore, selectInboxLimit, selectInboxSkip } from './inbox.selectors';

@Injectable()
export class InboxEffects {
    private actions$ = inject(Actions);
    private emailService = inject(EmailService);
    private smartLabelService = inject(SmartLabelService);
    private store = inject(Store);

    loadConnection$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadInboxConnection),
            switchMap(() =>
                this.emailService.getConnection().pipe(
                    map((connection) => loadInboxConnectionSuccess({ connection })),
                    catchError((error) => of(loadInboxConnectionFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadLabels$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadInboxLabels),
            switchMap(() =>
                this.smartLabelService.getAll(0, 50).pipe(
                    map((response) => loadInboxLabelsSuccess({ labels: response.items })),
                    catchError((error) => of(loadInboxLabelsFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    loadEmails$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadInboxEmails),
            withLatestFrom(
                this.store.select(selectInboxFilter),
                this.store.select(selectInboxSkip),
                this.store.select(selectInboxLimit),
            ),
            switchMap(([action, filter, skip, limit]) => {
                const effectiveSkip = action.reset ? 0 : skip;
                return this.emailService.getEmails(
                    effectiveSkip,
                    limit,
                    filter.folder || '',
                    '',
                    filter.smartLabel || '',
                ).pipe(
                    map((response) => loadInboxEmailsSuccess({ response, reset: !!action.reset })),
                    catchError((error) => of(loadInboxEmailsFailure({ error: errorMessage(error) }))),
                );
            }),
        ),
    );

    loadMore$ = createEffect(() =>
        this.actions$.pipe(
            ofType(loadMoreInboxEmails),
            withLatestFrom(this.store.select(selectInboxHasMore)),
            filter(([, hasMore]) => hasMore),
            map(() => loadInboxEmails({ reset: false })),
        ),
    );

    reloadAfterFilter$ = createEffect(() =>
        this.actions$.pipe(
            ofType(setInboxFilter),
            map(() => loadInboxEmails({ reset: true })),
        ),
    );

    refresh$ = createEffect(() =>
        this.actions$.pipe(
            ofType(refreshInboxEmails),
            exhaustMap(() =>
                this.emailService.triggerSync().pipe(
                    map(() => loadInboxEmails({ reset: true })),
                    catchError((error) => of(refreshInboxEmailsFailure({ error: errorMessage(error) }), loadInboxEmails({ reset: true }))),
                ),
            ),
        ),
    );

    send$ = createEffect(() =>
        this.actions$.pipe(
            ofType(sendInboxEmail),
            exhaustMap(({ request }) =>
                this.emailService.sendEmail(request).pipe(
                    map(() => sendInboxEmailSuccess()),
                    catchError((error) => of(sendInboxEmailFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    reply$ = createEffect(() =>
        this.actions$.pipe(
            ofType(replyInboxEmail),
            exhaustMap(({ id, request }) =>
                this.emailService.replyEmail(id, request).pipe(
                    map(() => replyInboxEmailSuccess()),
                    catchError((error) => of(replyInboxEmailFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    forward$ = createEffect(() =>
        this.actions$.pipe(
            ofType(forwardInboxEmail),
            exhaustMap(({ id, request }) =>
                this.emailService.forwardEmail(id, request).pipe(
                    map(() => forwardInboxEmailSuccess()),
                    catchError((error) => of(forwardInboxEmailFailure({ error: errorMessage(error) }))),
                ),
            ),
        ),
    );

    reloadAfterSend$ = createEffect(() =>
        this.actions$.pipe(
            ofType(sendInboxEmailSuccess, replyInboxEmailSuccess, forwardInboxEmailSuccess),
            map(() => loadInboxEmails({ reset: true })),
        ),
    );
}
