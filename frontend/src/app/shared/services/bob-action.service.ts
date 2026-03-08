import { Injectable, NgZone } from '@angular/core';
import { Router } from '@angular/router';
import { Subject, ReplaySubject } from 'rxjs';

export interface BobAction {
    type: 'navigate' | 'open_create_dialog' | 'change_slide' | 'ui_update_input' | 'ui_select_result' | 'ui_switch_tab';
    page?: string;
    entity?: string;
    name?: string;
    direction?: string;
    slide_number?: number;
    text?: string;
    submit?: boolean;
    index?: number;
}

export interface BobMission {
    missionPrompt: string;
    initialMessage: string;
    missionContext?: Record<string, unknown>;
}

@Injectable({ providedIn: 'root' })
export class BobActionService {
    /** Observable for page components to subscribe and react to Bob's actions. */
    readonly action$ = new Subject<BobAction>();

    /** Observable for bob-chat to start a mission-driven conversation. */
    readonly mission$ = new Subject<BobMission>();

    /** Observable for bob-chat to update an ongoing mission (e.g. slide change). */
    readonly missionUpdate$ = new Subject<BobMission>();

    constructor(private router: Router, private ngZone: NgZone) { }

    /**
     * Dispatch an action received from LLM function call result.
     * Called by bob-chat.ts when a function call event is received.
     */
    dispatch(action: BobAction): void {
        console.log('[BobAction] dispatch called:', JSON.stringify(action));
        const page = action.page || this.entityToPage(action.entity);
        console.log(`[BobAction] resolved page: '${page}', current URL: ${this.router.url}`);

        if (action.type === 'navigate' && action.page) {
            console.log(`[BobAction] navigating directly to /${action.page}...`);
            this.ngZone.run(() => {
                this.router.navigate([`/${action.page}`]).then((success) => {
                    console.log(`[BobAction] navigation result: ${success}, now at: ${this.router.url}`);
                });
            });
        }
        else if (page && action.type === 'open_create_dialog') {
            console.log(`[BobAction] navigating to /${page}...`);
            this.ngZone.run(() => {
                this.router.navigate([`/${page}`]).then((success) => {
                    console.log(`[BobAction] navigation result: ${success}, now at: ${this.router.url}`);
                    console.log(`[BobAction] emitting action$.next now`, JSON.stringify(action));
                    this.action$.next(action);
                });
            });
        } else {
            console.log('[BobAction] no routing needed — emitting action$.next directly');
            this.action$.next(action);
        }
    }

    /**
     * Start a mission-driven conversation with Bob.
     * Opens the chat panel and sends the initial message with mission context.
     * Starts a completely fresh session.
     */
    startMission(mission: BobMission): void {
        console.log('[BobAction] startMission:', mission.missionPrompt.substring(0, 80) + '...');
        this.mission$.next(mission);
    }

    /**
     * Update an ongoing mission without clearing the session.
     * Useful for injecting new context like changing a slide.
     */
    updateMission(mission: BobMission): void {
        console.log('[BobAction] updateMission:', mission.initialMessage);
        this.missionUpdate$.next(mission);
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
