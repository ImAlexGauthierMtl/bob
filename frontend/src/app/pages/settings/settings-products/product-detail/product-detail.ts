import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ProductService } from '../../../../shared/services/product.service';
import { Product, CreateProductDto, ProductCategory } from '../../../../shared/models/product.model';

const VALID_CATEGORIES: ProductCategory[] = ['SOFTWARE', 'SERVICE', 'ADD_ON', 'CONSULTING', 'HARDWARE'];

@Component({
    selector: 'croo-product-detail',
    standalone: true,
    imports: [FormsModule, RouterLink],
    templateUrl: './product-detail.html',
    styleUrls: ['./product-detail.css'],
})
export class ProductDetailComponent implements OnInit {
    product: Product | null = null;
    isLoading = true;
    isNew = false;
    isSaving = false;
    activeTab = 'overview';
    statusMessage = '';
    statusType: 'success' | 'error' = 'success';

    // Add-ons (for SERVICE products)
    addons: Product[] = [];
    showAddonDialog = false;
    addonForm: CreateProductDto = this.getEmptyAddonForm();
    isCreatingAddon = false;

    // Edit form
    formData: CreateProductDto = this.getEmptyForm();

    // Service products for add-on parent selection
    serviceProducts: Product[] = [];

    private route = inject(ActivatedRoute);
    private router = inject(Router);
    private productService = inject(ProductService);

    ngOnInit(): void {
        const id = this.route.snapshot.paramMap.get('id');
        if (id === 'new') {
            this.isNew = true;
            this.isLoading = false;
            this.formData = this.getEmptyForm();
            // Read category from query param
            const type = this.route.snapshot.queryParamMap.get('type') as ProductCategory;
            if (type && VALID_CATEGORIES.includes(type)) {
                this.formData.category = type;
            }
            this.activeTab = 'configuration';
            if (this.formData.category === 'ADD_ON') {
                this.loadServiceProducts();
            }
        } else if (id) {
            this.loadProduct(id);
        }
    }

    loadProduct(id: string): void {
        this.isLoading = true;
        this.productService.getById(id).subscribe({
            next: (p) => {
                this.product = p;
                this.formData = this.productToForm(p);
                this.isLoading = false;
                if (p.category === 'SERVICE') {
                    this.loadAddons(p.id);
                }
                if (p.category === 'ADD_ON') {
                    this.loadServiceProducts();
                }
            },
            error: () => {
                this.isLoading = false;
                this.router.navigate(['/settings/products']);
            },
        });
    }

    loadAddons(parentId: string): void {
        this.productService.getAll(0, 200, 'ADD_ON', parentId).subscribe({
            next: (res) => this.addons = res.items,
        });
    }

    loadServiceProducts(): void {
        this.productService.getServices().subscribe({
            next: (items) => this.serviceProducts = items,
        });
    }

    // ── Tabs ────────────────────────────────

    setActiveTab(tab: string): void {
        this.activeTab = tab;
    }

    getTabs(): { key: string; label: string }[] {
        const tabs = [
            { key: 'overview', label: 'Overview' },
            { key: 'configuration', label: 'Configuration' },
        ];
        const cat = this.isNew ? this.formData.category : this.product?.category;
        if (cat === 'SERVICE') {
            tabs.push({ key: 'addons', label: `Add-Ons (${this.addons.length})` });
        }
        return tabs;
    }

    // ── Save / Create ────────────────────────────────

    saveProduct(): void {
        if (!this.formData.name.trim()) return;
        this.isSaving = true;
        this.statusMessage = '';

        if (this.isNew) {
            this.productService.create(this.formData).subscribe({
                next: (p) => {
                    this.isSaving = false;
                    this.router.navigate(['/settings/products', p.id]);
                },
                error: () => {
                    this.isSaving = false;
                    this.statusMessage = '❌ Failed to create product.';
                    this.statusType = 'error';
                },
            });
        } else if (this.product) {
            this.productService.update(this.product.id, this.formData).subscribe({
                next: (p) => {
                    this.product = p;
                    this.formData = this.productToForm(p);
                    this.isSaving = false;
                    this.statusMessage = '✅ Product saved.';
                    this.statusType = 'success';
                    setTimeout(() => this.statusMessage = '', 3000);
                },
                error: () => {
                    this.isSaving = false;
                    this.statusMessage = '❌ Failed to save.';
                    this.statusType = 'error';
                },
            });
        }
    }

    deleteProduct(): void {
        if (!this.product) return;
        this.productService.delete(this.product.id).subscribe({
            next: () => this.router.navigate(['/settings/products']),
        });
    }

    // ── Add-on Dialog ────────────────────────────────

    openAddonDialog(): void {
        this.addonForm = this.getEmptyAddonForm();
        if (this.product) {
            this.addonForm.parent_product_id = this.product.id;
            // Inherit billing from parent
            this.addonForm.billing_cycle = this.product.billing_cycle || undefined;
            this.addonForm.contract_term_months = this.product.contract_term_months || undefined;
        }
        this.showAddonDialog = true;
    }

    closeAddonDialog(): void {
        this.showAddonDialog = false;
    }

    createAddon(): void {
        if (!this.addonForm.name.trim()) return;
        this.isCreatingAddon = true;
        this.productService.create(this.addonForm).subscribe({
            next: () => {
                this.isCreatingAddon = false;
                this.showAddonDialog = false;
                if (this.product) this.loadAddons(this.product.id);
            },
            error: () => this.isCreatingAddon = false,
        });
    }

    deleteAddon(addon: Product): void {
        this.productService.delete(addon.id).subscribe({
            next: () => {
                if (this.product) this.loadAddons(this.product.id);
            },
        });
    }

    // ── Helpers ────────────────────────────────

    getCategoryClass(category: string): string {
        switch (category) {
            case 'SOFTWARE': return 'category--blue';
            case 'SERVICE': return 'category--green';
            case 'ADD_ON': return 'category--purple';
            case 'CONSULTING': return 'category--orange';
            case 'HARDWARE': return 'category--gray';
            default: return 'category--blue';
        }
    }

    getCategoryIcon(category: string): string {
        switch (category) {
            case 'SOFTWARE': return 'fa-solid fa-laptop-code';
            case 'SERVICE': return 'fa-solid fa-cloud';
            case 'ADD_ON': return 'fa-solid fa-puzzle-piece';
            case 'CONSULTING': return 'fa-solid fa-briefcase';
            case 'HARDWARE': return 'fa-solid fa-microchip';
            default: return 'fa-solid fa-box';
        }
    }

    getCategoryLabel(category: string): string {
        switch (category) {
            case 'ADD_ON': return 'ADD-ON';
            default: return category;
        }
    }

    formatPrice(price: number, currency?: string): string {
        const sym = currency === 'EUR' ? '€' : '$';
        return sym + price.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    getBillingLabel(cycle: string | null | undefined): string {
        if (!cycle) return '';
        switch (cycle) {
            case 'MONTHLY': return 'Monthly';
            case 'QUARTERLY': return 'Quarterly';
            case 'SEMI_ANNUAL': return 'Semi-Annual';
            case 'ANNUAL': return 'Annual';
            default: return cycle;
        }
    }

    private productToForm(p: Product): CreateProductDto {
        return {
            name: p.name,
            description: p.description || undefined,
            category: p.category,
            unit_price: p.unit_price,
            currency: p.currency,
            sku: p.sku || undefined,
            is_active: p.is_active,
            is_taxable: p.is_taxable,
            tax_rate: p.tax_rate || undefined,
            min_quantity: p.min_quantity || undefined,
            max_quantity: p.max_quantity || undefined,
            billing_cycle: p.billing_cycle || undefined,
            contract_term_months: p.contract_term_months || undefined,
            auto_renew: p.auto_renew ?? undefined,
            setup_fee: p.setup_fee || undefined,
            trial_days: p.trial_days || undefined,
            parent_product_id: p.parent_product_id || undefined,
            is_coterminus: p.is_coterminus ?? undefined,
            license_type: p.license_type || undefined,
            max_users: p.max_users || undefined,
            billing_unit: p.billing_unit || undefined,
            estimated_hours: p.estimated_hours || undefined,
            weight_kg: p.weight_kg || undefined,
            warranty_months: p.warranty_months || undefined,
            manufacturer: p.manufacturer || undefined,
            part_number: p.part_number || undefined,
        };
    }

    private getEmptyForm(): CreateProductDto {
        return {
            name: '', category: 'SOFTWARE', unit_price: 0, currency: 'CAD',
            is_active: true, is_taxable: true, auto_renew: true, is_coterminus: true,
        };
    }

    private getEmptyAddonForm(): CreateProductDto {
        return {
            name: '', category: 'ADD_ON', unit_price: 0, currency: 'CAD',
            is_active: true, is_taxable: true, auto_renew: true, is_coterminus: true,
        };
    }
}
