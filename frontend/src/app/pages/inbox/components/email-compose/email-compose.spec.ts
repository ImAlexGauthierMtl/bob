import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideMockStore } from '@ngrx/store/testing';

import { EmailComposeComponent } from './email-compose';
import { initialInboxState } from '../../../../store/inbox/inbox.reducer';

describe('EmailCompose', () => {
  let component: EmailComposeComponent;
  let fixture: ComponentFixture<EmailComposeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailComposeComponent],
      providers: [provideMockStore({ initialState: { inbox: initialInboxState } })],
    }).compileComponents();

    fixture = TestBed.createComponent(EmailComposeComponent);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
