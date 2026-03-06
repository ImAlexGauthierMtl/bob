import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

@Component({
    selector: 'croo-settings',
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive],
    templateUrl: './settings.html',
    styleUrl: './settings.css',
})
export class SettingsComponent { }
