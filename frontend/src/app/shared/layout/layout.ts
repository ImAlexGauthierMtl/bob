import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { BobChatComponent } from '../bob-chat/bob-chat';

@Component({
    selector: 'croo-layout',
    standalone: true,
    imports: [RouterOutlet, RouterLink, RouterLinkActive, BobChatComponent],
    templateUrl: './layout.html',
    styleUrl: './layout.css',
})
export class LayoutComponent { }
