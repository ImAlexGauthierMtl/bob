import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'croo-organizations',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './organizations.html',
    styleUrl: './organizations.css',
})
export class OrganizationsComponent { }
