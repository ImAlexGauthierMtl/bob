import { ApplicationConfig, provideBrowserGlobalErrorListeners, provideZoneChangeDetection } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideEffects } from '@ngrx/effects';
import { provideStore } from '@ngrx/store';
import { provideStoreDevtools } from '@ngrx/store-devtools';

import 'zone.js';

import { routes } from './app.routes';
import { authInterceptor } from './shared/interceptors/auth.interceptor';
import { appEffects, appReducers, storeDevtoolsOptions } from './store';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideStore(appReducers),
    provideEffects(appEffects),
    provideStoreDevtools(storeDevtoolsOptions),
  ]
};
