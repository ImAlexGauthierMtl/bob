# Template: Pipe Sanitize HTML (Angular)

> Pipe pour injecter du HTML de façon sécurisée.

## Fichier

`core/pipes/sanitize-html.pipe.ts`

```typescript
import { Pipe, PipeTransform } from '@angular/core';
import { DomSanitizer, SafeHtml } from '@angular/platform-browser';

@Pipe({ name: 'sanitizeHtml', standalone: true })
export class SanitizeHtmlPipe implements PipeTransform {
  constructor(private sanitizer: DomSanitizer) {}

  transform(value: string): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(value);
  }
}
```

## Utilisation

```html
<div [innerHTML]="htmlContent | sanitizeHtml"></div>
```

## Règle : N'utiliser que pour du contenu de confiance (généré par le backend).
