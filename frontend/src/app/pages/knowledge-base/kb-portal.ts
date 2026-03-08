import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { DatePipe, DecimalPipe } from '@angular/common';
import { KnowledgeBaseService } from '../../shared/services/kb.service';
import { KBCategory, KBArticleSummary, KBStats } from '../../shared/models/kb.model';

@Component({
    selector: 'app-kb-portal',
    standalone: true,
    imports: [FormsModule, RouterLink, DatePipe, DecimalPipe],
    templateUrl: './kb-portal.html',
    styleUrl: './kb-portal.css',
})
export class KBPortalComponent implements OnInit {
    categories: KBCategory[] = [];
    popularArticles: KBArticleSummary[] = [];
    recentArticles: KBArticleSummary[] = [];
    searchResults: KBArticleSummary[] = [];
    stats: KBStats = {
        total_articles: 0,
        published_articles: 0,
        total_categories: 0,
        total_views: 0,
        avg_helpfulness: 0,
    };

    searchQuery = '';
    isSearching = false;

    // Category icon map (fallback if not stored in DB)
    iconMap: Record<string, string> = {
        'getting-started': 'fa-solid fa-rocket',
        'sales-crm': 'fa-solid fa-chart-line',
        'ai-features': 'fa-solid fa-wand-magic-sparkles',
        'automation': 'fa-solid fa-gears',
        'team-management': 'fa-solid fa-users-gear',
        'security-privacy': 'fa-solid fa-shield-halved',
        'api-integrations': 'fa-solid fa-code',
        'admin': 'fa-solid fa-shield-halved',
        'api': 'fa-solid fa-code',
    };

    colorMap: Record<string, string> = {
        'getting-started': '#3b82f6',
        'sales-crm': '#10b981',
        'ai-features': '#a855f7',
        'automation': '#f59e0b',
        'team-management': '#f97316',
        'security-privacy': '#ef4444',
        'api-integrations': '#eab308',
        'admin': '#ef4444',
        'api': '#6366f1',
    };

    private kbService = inject(KnowledgeBaseService);

    ngOnInit(): void {
        this.loadCategories();
        this.loadPopular();
        this.loadRecent();
        this.loadStats();
    }

    loadCategories(): void {
        this.kbService.listCategories().subscribe({
            next: (res) => (this.categories = res.items),
        });
    }

    loadPopular(): void {
        this.kbService.popularArticles(8).subscribe({
            next: (articles) => (this.popularArticles = articles),
        });
    }

    loadRecent(): void {
        this.kbService.listArticles({ limit: 3 }).subscribe({
            next: (res) => (this.recentArticles = res.items),
        });
    }

    loadStats(): void {
        this.kbService.getStats().subscribe({
            next: (s) => (this.stats = s),
        });
    }

    onSearch(): void {
        if (!this.searchQuery.trim()) {
            this.isSearching = false;
            this.searchResults = [];
            return;
        }
        this.isSearching = true;
        this.kbService
            .listArticles({ search: this.searchQuery, limit: 20 })
            .subscribe({
                next: (res) => (this.searchResults = res.items),
            });
    }

    clearSearch(): void {
        this.searchQuery = '';
        this.isSearching = false;
        this.searchResults = [];
    }

    getCategoryIcon(cat: KBCategory): string {
        return cat.icon || this.iconMap[cat.slug] || 'fa-solid fa-book';
    }

    getCategoryColor(cat: KBCategory): string {
        return cat.color || this.colorMap[cat.slug] || '#6b7280';
    }

    getCategoryName(categoryId: string | null): string {
        if (!categoryId) return 'General';
        const cat = this.categories.find(c => c.id === categoryId);
        return cat?.name || 'General';
    }
}
