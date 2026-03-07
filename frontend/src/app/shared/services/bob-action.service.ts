import { Injectable, NgZone } from '@angular/core';
import { Router } from '@angular/router';
import { Subject } from 'rxjs';

export interface BobAction {
    type: 'navigate' | 'open_create_dialog';
    page?: string;
    entity?: string;
    name?: string;
}

@Injectable({ providedIn: 'root' })
export class BobActionService {
    /** Observable for page components to subscribe and react to Bob's actions. */
    readonly action$ = new Subject<BobAction>();

    constructor(private router: Router, private ngZone: NgZone) { }

    /**
     * Dispatch an action received from LLM function call result.
     * Called by bob-chat.ts when a function call event is received.
     */
    dispatch(action: BobAction): void {
        console.log('[BobAction] dispatch called:', JSON.stringify(action));
        const page = action.page || this.entityToPage(action.entity);
        console.log(`[BobAction] resolved page: '${page}', current URL: ${this.router.url}`);

        if (page) {
            console.log(`[BobAction] navigating to /${page}...`);
            // Run inside NgZone to ensure Angular detects the navigation
            this.ngZone.run(() => {
                this.router.navigate([`/${page}`]).then((success) => {
                    console.log(`[BobAction] navigation result: ${success}, now at: ${this.router.url}`);
                    if (action.type === 'open_create_dialog') {
                        console.log(`[BobAction] scheduling action$.next in 500ms for entity: ${action.entity}`);
                        setTimeout(() => {
                            console.log(`[BobAction] emitting action$.next now`, JSON.stringify(action));
                            this.action$.next(action);
                        }, 500);
                    }
                });
            });
        } else {
            console.log('[BobAction] no page — emitting action$.next directly');
            this.action$.next(action);
        }
    }

    /** Map entity name to route path. */
    private entityToPage(entity?: string): string {
        const map: Record<string, string> = {
            organization: 'organizations',
            contact: 'contacts',
            opportunity: 'opportunities',
            quote: 'quotes',
            activity: 'activities',
        };
        return entity ? map[entity] || '' : '';
    }
}
