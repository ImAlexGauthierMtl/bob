import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Router } from '@angular/router';
import { Subscription } from 'rxjs';
import { BobActionService, BobAction, BobDisplayItem, BobDisplayStat } from '../services/bob-action.service';

@Component({
    selector: 'croo-bob-display-overlay',
    standalone: true,
    imports: [],
    templateUrl: './bob-display-overlay.html',
    styleUrl: './bob-display-overlay.css',
})
export class BobDisplayOverlayComponent implements OnInit, OnDestroy {
    private actionSub?: Subscription;
    private bobActionService = inject(BobActionService);
    private router = inject(Router);

    isVisible = false;
    displayType: 'list' | 'stats' | 'detail' = 'list';
    title = '';
    subtitle = '';
    icon = 'fa-solid fa-robot';
    items: BobDisplayItem[] = [];
    stats: BobDisplayStat[] = [];

    ngOnInit(): void {
        this.actionSub = this.bobActionService.action$.subscribe((action: BobAction) => {
            if (action.type === 'bob_display') {
                this.showDisplay(action);
            }
        });
    }

    ngOnDestroy(): void {
        this.actionSub?.unsubscribe();
    }

    showDisplay(action: BobAction): void {
        this.displayType = action.display_type || 'list';
        this.title = action.title || 'Bob Results';
        this.subtitle = action.subtitle || '';
        this.icon = action.icon || 'fa-solid fa-robot';
        this.items = action.items || [];
        this.stats = action.stats || [];
        this.isVisible = true;
    }

    close(): void {
        this.isVisible = false;
    }

    navigateToItem(item: BobDisplayItem): void {
        if (item.route) {
            this.router.navigate([item.route]);
            this.close();
        }
    }

    getTrendIcon(trend?: string): string {
        switch (trend) {
            case 'up': return 'fa-solid fa-arrow-trend-up';
            case 'down': return 'fa-solid fa-arrow-trend-down';
            default: return 'fa-solid fa-minus';
        }
    }

    getTrendColor(trend?: string): string {
        switch (trend) {
            case 'up': return '#22c55e';
            case 'down': return '#ef4444';
            default: return 'var(--color-gray-400)';
        }
    }
}
