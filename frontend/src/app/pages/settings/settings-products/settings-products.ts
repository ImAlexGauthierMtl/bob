import { Component, OnInit, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { ProductService } from '../../../shared/services/product.service';
import { Product, ProductCategory } from '../../../shared/models/product.model';

@Component({
    selector: 'croo-settings-products',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './settings-products.html',
    styleUrls: ['../settings-shared.css', './settings-products.css'],
})
export class SettingsProductsComponent implements OnInit {
    products: Product[] = [];
    total = 0;
    isLoading = true;

    currentPage = 1;
    pageSize = 50;
    totalPages = 1;
    Math = Math;

    activeFilter: ProductCategory | 'ALL' = 'ALL';
    showNewDropdown = false;

    private productService = inject(ProductService);
    private router = inject(Router);

    ngOnInit(): void {
        this.loadProducts();
    }

    loadProducts(): void {
        this.isLoading = true;
        const skip = (this.currentPage - 1) * this.pageSize;
        const category = this.activeFilter === 'ALL' ? undefined : this.activeFilter;
        this.productService.getAll(skip, this.pageSize, category).subscribe({
            next: (res) => {
                this.products = res.items;
                this.total = res.total;
                this.totalPages = Math.max(1, Math.ceil(this.total / this.pageSize));
                this.isLoading = false;
            },
            error: () => (this.isLoading = false),
        });
    }

    setFilter(filter: ProductCategory | 'ALL'): void {
        this.activeFilter = filter;
        this.currentPage = 1;
        this.loadProducts();
    }

    goToPage(page: number): void {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        this.loadProducts();
    }

    onPageSizeChange(event: Event): void {
        this.pageSize = +(event.target as HTMLSelectElement).value;
        this.currentPage = 1;
        this.loadProducts();
    }

    getPages(): number[] {
        const pages: number[] = [];
        const max = Math.min(this.totalPages, 5);
        let start = Math.max(1, this.currentPage - Math.floor(max / 2));
        const end = Math.min(this.totalPages, start + max - 1);
        start = Math.max(1, end - max + 1);
        for (let i = start; i <= end; i++) pages.push(i);
        return pages;
    }

    openProduct(product: Product): void {
        this.router.navigate(['/settings/products', product.id]);
    }

    toggleNewDropdown(): void {
        this.showNewDropdown = !this.showNewDropdown;
    }

    createProduct(category: ProductCategory): void {
        this.showNewDropdown = false;
        this.router.navigate(['/settings/products', 'new'], { queryParams: { type: category } });
    }

    getCategoryClass(category: string): string {
        switch (category) {
            case 'SOFTWARE': return 'category-badge--blue';
            case 'SERVICE': return 'category-badge--green';
            case 'ADD_ON': return 'category-badge--purple';
            case 'CONSULTING': return 'category-badge--orange';
            case 'HARDWARE': return 'category-badge--gray';
            default: return 'category-badge--blue';
        }
    }

    getCategoryLabel(category: string): string {
        return category === 'ADD_ON' ? 'ADD-ON' : category;
    }

    formatPrice(price: number): string {
        return '$' + price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    getBillingLabel(cycle: string | null): string {
        if (!cycle) return '';
        switch (cycle) {
            case 'MONTHLY': return '/mo';
            case 'QUARTERLY': return '/qtr';
            case 'SEMI_ANNUAL': return '/6mo';
            case 'ANNUAL': return '/yr';
            default: return '';
        }
    }

    getBillingUnitLabel(unit: string | null): string {
        if (!unit) return '';
        switch (unit) {
            case 'HOUR': return '/hr';
            case 'DAY': return '/day';
            case 'PROJECT': return '/project';
            case 'RETAINER': return '/retainer';
            default: return '';
        }
    }

    getSubInfo(product: Product): string {
        switch (product.category) {
            case 'SERVICE':
            case 'ADD_ON':
                const parts: string[] = [];
                if (product.billing_cycle) parts.push(product.billing_cycle.replace('_', ' ').toLowerCase());
                if (product.contract_term_months) parts.push(`${product.contract_term_months}mo term`);
                return parts.join(' · ');
            case 'SOFTWARE':
                return product.license_type?.replace('_', ' ').toLowerCase() || '';
            case 'CONSULTING':
                return product.billing_unit ? `per ${product.billing_unit.toLowerCase()}` : '';
            case 'HARDWARE':
                return product.manufacturer || '';
            default:
                return '';
        }
    }
}
