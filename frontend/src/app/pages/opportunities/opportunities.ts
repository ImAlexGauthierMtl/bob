import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'croo-opportunities',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './opportunities.html',
    styleUrl: './opportunities.css',
})
export class OpportunitiesComponent { }
