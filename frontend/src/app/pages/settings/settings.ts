import { Component, OnDestroy, OnInit } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Subscription } from 'rxjs';
import { filter } from 'rxjs/operators';

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

    constructor(private router: Router) { }

    ngOnInit(): void {
        this.checkRoute(this.router.url);
        this.routerSub = this.router.events
            .pipe(filter((e): e is NavigationEnd => e instanceof NavigationEnd))
            .subscribe((e) => this.checkRoute(e.urlAfterRedirects));
    }

    ngOnDestroy(): void {
        this.routerSub?.unsubscribe();
    }

    private checkRoute(url: string): void {
        this.isFullWidth = url.includes('/settings/automation') || url.includes('/settings/bob/capabilities');
    }
}
