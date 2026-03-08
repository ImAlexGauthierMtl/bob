import { inject, Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Product, CreateProductDto, ProductListResponse } from '../models/product.model';
import { environment } from '../../../environments/environment';

const API_URL = `${environment.apiUrl}`;

@Injectable({ providedIn: 'root' })
export class ProductService {
    private http = inject(HttpClient);

    getAll(skip = 0, limit = 50, category?: string, parentProductId?: string): Observable<ProductListResponse> {
        let url = `${API_URL}/products?skip=${skip}&limit=${limit}`;
        if (category) url += `&category=${category}`;
        if (parentProductId) url += `&parent_product_id=${parentProductId}`;
        return this.http.get<ProductListResponse>(url);
    }

    getServices(): Observable<Product[]> {
        return this.http.get<Product[]>(`${API_URL}/products/services`);
    }

    getById(id: string): Observable<Product> {
        return this.http.get<Product>(`${API_URL}/products/${id}`);
    }

    create(data: CreateProductDto): Observable<Product> {
        return this.http.post<Product>(`${API_URL}/products`, data);
    }

    update(id: string, data: Partial<CreateProductDto>): Observable<Product> {
        return this.http.patch<Product>(`${API_URL}/products/${id}`, data);
    }

    delete(id: string): Observable<void> {
        return this.http.delete<void>(`${API_URL}/products/${id}`);
    }
}
