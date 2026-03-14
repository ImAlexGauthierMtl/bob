import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EmailCompose } from './email-compose';

describe('EmailCompose', () => {
  let component: EmailCompose;
  let fixture: ComponentFixture<EmailCompose>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EmailCompose],
    }).compileComponents();

    fixture = TestBed.createComponent(EmailCompose);
    component = fixture.componentInstance;
    await fixture.whenStable();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
