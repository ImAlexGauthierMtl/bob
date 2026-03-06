import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
    selector: 'croo-contacts',
    standalone: true,
    imports: [RouterLink],
    templateUrl: './contacts.html',
    styleUrl: './contacts.css',
})
export class ContactsComponent { }
