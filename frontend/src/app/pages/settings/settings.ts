import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';
import { BobActionService } from '../../shared/services/bob-action.service';

@Component({
    selector: 'croo-settings',
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive],
    templateUrl: './settings.html',
    styleUrl: './settings.css',
})
export class SettingsComponent implements OnInit, OnDestroy {
    isFullWidth = false;
    private routerSub!: Subscription;
    private bobActionSub?: Subscription;

    constructor(
        private router: Router,
        private bobAction: BobActionService
    ) { }

    ngOnInit(): void {
        this.checkRoute(this.router.url);
        this.routerSub = this.router.events
            .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
            .subscribe((e) => this.checkRoute(e.urlAfterRedirects));

        this.bobActionSub = this.bobAction.action$.subscribe(action => {
            if (action.type === 'ui_switch_tab' && action.name) {
                const search = action.name.toLowerCase();

                const tabMap: { [key: string]: string } = {
                    'profile': 'profile',
                    'security': 'security',
                    'account': 'security',
                    'notification': 'notifications',
                    'notifications': 'notifications',
                    'bob': 'bob',
                    'assistant': 'bob',
                    'automation': 'automation',
                    'control center': 'bob-control-center',
                    'bcc': 'bob-control-center',
                    'team': 'team',
                    'member': 'team',
                    'roles': 'roles',
                    'permissions': 'roles',
                    'integration': 'integrations',
                    'integrations': 'integrations'
                };

                let targetRoute = null;
                for (const key of Object.keys(tabMap)) {
                    if (search.includes(key) || key.includes(search)) {
                        targetRoute = tabMap[key];
                        break;
                    }
                }

                if (targetRoute) {
                    this.router.navigate(['/settings', targetRoute]);
                }
            }
        });
    }

    ngOnDestroy(): void {
        this.routerSub?.unsubscribe();
        this.bobActionSub?.unsubscribe();
    }

    private checkRoute(url: string): void {
        this.isFullWidth = url.includes('/settings/automation') || url.includes('/settings/bob/capabilities') || url.includes('/settings/bob-control-center');
    }
}
