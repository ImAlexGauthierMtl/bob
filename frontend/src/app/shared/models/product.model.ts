export type ProductCategory = 'SOFTWARE' | 'SERVICE' | 'ADD_ON' | 'CONSULTING' | 'HARDWARE';
export type BillingCycle = 'MONTHLY' | 'QUARTERLY' | 'SEMI_ANNUAL' | 'ANNUAL';
export type LicenseType = 'PERPETUAL' | 'SUBSCRIPTION' | 'USAGE_BASED';
export type BillingUnit = 'HOUR' | 'DAY' | 'PROJECT' | 'RETAINER';

export interface Product {
    id: string;
    // Common
    name: string;
    description: string | null;
    category: ProductCategory;
    unit_price: number;
    currency: string;
    sku: string | null;
    is_active: boolean;
    is_taxable: boolean;
    tax_rate: number | null;
    min_quantity: number | null;
    max_quantity: number | null;
    // SaaS
    billing_cycle: BillingCycle | null;
    contract_term_months: number | null;
    auto_renew: boolean | null;
    setup_fee: number | null;
    trial_days: number | null;
    // Add-on
    parent_product_id: string | null;
    is_coterminus: boolean | null;
    // Software
    license_type: LicenseType | null;
    max_users: number | null;
    // Consulting
    billing_unit: BillingUnit | null;
    estimated_hours: number | null;
    // Hardware
    weight_kg: number | null;
    warranty_months: number | null;
    manufacturer: string | null;
    part_number: string | null;
    // Audit
    created_at: string;
    updated_at: string;
}

export interface CreateProductDto {
    name: string;
    description?: string;
    category: ProductCategory;
    unit_price: number;
    currency?: string;
    sku?: string;
    is_active?: boolean;
    is_taxable?: boolean;
    tax_rate?: number;
    min_quantity?: number;
    max_quantity?: number;
    // SaaS
    billing_cycle?: BillingCycle;
    contract_term_months?: number;
    auto_renew?: boolean;
    setup_fee?: number;
    trial_days?: number;
    // Add-on
    parent_product_id?: string;
    is_coterminus?: boolean;
    // Software
    license_type?: LicenseType;
    max_users?: number;
    // Consulting
    billing_unit?: BillingUnit;
    estimated_hours?: number;
    // Hardware
    weight_kg?: number;
    warranty_months?: number;
    manufacturer?: string;
    part_number?: string;
}

export interface ProductListResponse {
    items: Product[];
    total: number;
    skip: number;
    limit: number;
}
