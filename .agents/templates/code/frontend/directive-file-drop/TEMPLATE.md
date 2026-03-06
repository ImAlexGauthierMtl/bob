# Template: Directive File Drop (Angular)

> Zone de drag & drop pour fichiers.

## Fichier

`shared/directives/file-drop.directive.ts`

```typescript
import { Directive, Output, EventEmitter, HostListener, HostBinding } from '@angular/core';

@Directive({ selector: '[appFileDrop]', standalone: true })
export class FileDropDirective {
  @Output() filesDropped = new EventEmitter<FileList>();
  @HostBinding('class.dragover') isDragOver = false;

  @HostListener('dragover', ['$event'])
  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = true;
  }

  @HostListener('dragleave', ['$event'])
  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
  }

  @HostListener('drop', ['$event'])
  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragOver = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.filesDropped.emit(files);
    }
  }
}
```

## Utilisation

```html
<div appFileDrop (filesDropped)="onFiles($event)" class="drop-zone">
  Glissez vos fichiers ici
</div>
```

## CSS pour `.dragover`

```scss
.drop-zone { border: 2px dashed #d1d5db; border-radius: 8px; padding: 40px; text-align: center; transition: all 0.2s; }
.drop-zone.dragover { border-color: var(--primary); background: rgba(79,70,229,0.05); }
```
