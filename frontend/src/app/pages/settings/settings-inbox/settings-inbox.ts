import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

import { SmartLabel } from '../../../shared/models/smart-label.model';
import { SmartLabelService } from '../../../shared/services/smart-label.service';
import { finalize } from 'rxjs';

@Component({
    selector: 'croo-settings-inbox',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './settings-inbox.html',
    styleUrls: ['../settings-shared.css', './settings-inbox.css'],
})
export class SettingsInboxComponent {
    isLoading = false;
    isSaving = false;
    saveMessage = '';
    saveType: 'success' | 'error' = 'success';

    constructor(private smartLabelService: SmartLabelService) {}

    ngOnInit(): void {
        this.loadLabels();
    }

    loadLabels(): void {
        this.isLoading = true;
        this.smartLabelService.getAll(0, 50)
            .pipe(finalize(() => this.isLoading = false))
            .subscribe({
                next: (res) => {
                    this.smartLabels = res.items;
                },
                error: (err) => {
                    console.error('Failed to load smart labels', err);
                    this.showToast('Failed to load labels', 'error');
                }
            });
    }

    // UI state for adding new label
    showAddForm = false;
    newLabelName = '';
    newLabelColor = 'blue';

    // Available colors for the BEM classes (e.g. inbox-nav__dot--blue)
    availableColors = [
        { value: 'blue', label: 'Blue', hex: '#686862' },
        { value: 'green', label: 'Green', hex: '#22c55e' },
        { value: 'purple', label: 'Purple', hex: '#a855f7' },
        { value: 'orange', label: 'Orange', hex: '#f97316' },
        { value: 'red', label: 'Red', hex: '#ef4444' },
    ];

    // Dynamic smart labels from API
    smartLabels: SmartLabel[] = [];

    // Parent edit state
    editingLabelId: string | null = null;
    editName = '';
    editColor = '';
    editDescription = '';
    editKeywordsRaw = '';
    editPromptHint = '';

    // Sub-label edit state (independent from parent)
    editingSubLabelId: string | null = null;
    subEditName = '';
    subEditColor = '';
    subEditDescription = '';
    subEditKeywordsRaw = '';
    subEditPromptHint = '';

    // Sub-category add state
    addingSubLabelToId: string | null = null;
    newSubLabelName = '';
    newSubLabelColor = 'blue';

    toggleAddForm(): void {
        this.showAddForm = !this.showAddForm;
        if (!this.showAddForm) {
            this.resetForm();
        }
    }

    resetForm(): void {
        this.newLabelName = '';
        this.newLabelColor = 'blue';
        this.showAddForm = false;
    }

    addLabel(): void {
        if (!this.newLabelName.trim()) return;

        this.isSaving = true;
        const payload = {
            name: this.newLabelName.trim(),
            color: this.newLabelColor
        };

        this.smartLabelService.create(payload)
            .pipe(finalize(() => this.isSaving = false))
            .subscribe({
                next: (newLabel) => {
                    this.smartLabels.push(newLabel);
                    this.resetForm();
                    this.showToast('Smart label added successfully', 'success');
                },
                error: (err) => {
                    console.error('Failed to create label', err);
                    this.showToast(err.error?.detail || 'Failed to create smart label', 'error');
                }
            });
    }

    removeLabel(id: string): void {
        this.smartLabelService.delete(id).subscribe({
            next: () => {
                this.smartLabels = this.smartLabels.filter(label => label.id !== id);
                if (this.editingLabelId === id) this.editingLabelId = null;
                this.showToast('Smart label removed', 'success');
            },
            error: (err) => {
                console.error('Failed to delete label', err);
                this.showToast('Failed to delete smart label', 'error');
            }
        });
    }

    // ── Sub-Category Actions ─────────────────────────

    toggleAddSubLabel(parentId: string): void {
        if (this.addingSubLabelToId === parentId) {
            this.addingSubLabelToId = null;
        } else {
            this.addingSubLabelToId = parentId;
            this.newSubLabelName = '';
            this.newSubLabelColor = 'blue';
        }
    }

    cancelAddSubLabel(): void {
        this.addingSubLabelToId = null;
        this.newSubLabelName = '';
    }

    addSubLabel(parentId: string): void {
        if (!this.newSubLabelName.trim()) return;

        this.isSaving = true;
        const payload = {
            name: this.newSubLabelName.trim(),
            color: this.newSubLabelColor,
            parent_id: parentId
        };

        this.smartLabelService.create(payload)
            .pipe(finalize(() => this.isSaving = false))
            .subscribe({
                next: (newLabel) => {
                    const parentIdx = this.smartLabels.findIndex(l => l.id === parentId);
                    if (parentIdx !== -1) {
                        const parent = this.smartLabels[parentIdx];
                        if (!parent.sub_labels) parent.sub_labels = [];
                        parent.sub_labels.push(newLabel);
                    }
                    this.addingSubLabelToId = null;
                    this.newSubLabelName = '';
                    this.showToast('Sub-category added properly', 'success');
                },
                error: (err) => {
                    console.error('Failed to create sub_label', err);
                    this.showToast(err.error?.detail || 'Failed to create sub-category', 'error');
                }
            });
    }

    removeSubLabel(parentId: string, subLabelId: string): void {
        this.smartLabelService.delete(subLabelId).subscribe({
            next: () => {
                const parentIdx = this.smartLabels.findIndex(l => l.id === parentId);
                if (parentIdx !== -1) {
                    const parent = this.smartLabels[parentIdx];
                    if (parent.sub_labels) {
                        parent.sub_labels = parent.sub_labels.filter(sl => sl.id !== subLabelId);
                    }
                }
                this.showToast('Sub-category removed', 'success');
            },
            error: (err) => {
                console.error('Failed to delete sub label', err);
                this.showToast('Failed to delete sub-category', 'error');
            }
        });
    }

    // ── Parent Label Edit ─────────────────────────────

    toggleEdit(labelId: string): void {
        if (this.editingLabelId === labelId) {
            this.editingLabelId = null;
            this.editingSubLabelId = null;
            this.addingSubLabelToId = null;
            return;
        }

        const label = this.smartLabels.find(l => l.id === labelId);
        if (!label) return;

        this.editingLabelId = labelId;
        this.editingSubLabelId = null;
        this.editName = label.name;
        this.editColor = label.color;
        this.editDescription = label.description || '';
        this.editKeywordsRaw = (label.keywords || []).join(', ');
        this.editPromptHint = label.prompt_hint || '';
    }

    // ── Sub-Label Edit (keeps parent open) ────────────

    toggleSubLabelEdit(subLabelId: string): void {
        if (this.editingSubLabelId === subLabelId) {
            this.editingSubLabelId = null;
            return;
        }

        let found: SmartLabel | undefined;
        for (const parent of this.smartLabels) {
            if (parent.sub_labels) {
                found = parent.sub_labels.find(sl => sl.id === subLabelId);
                if (found) break;
            }
        }
        if (!found) return;

        this.editingSubLabelId = subLabelId;
        this.subEditName = found.name;
        this.subEditColor = found.color;
        this.subEditDescription = found.description || '';
        this.subEditKeywordsRaw = (found.keywords || []).join(', ');
        this.subEditPromptHint = found.prompt_hint || '';
    }

    cancelEdit(): void {
        this.editingLabelId = null;
        this.editingSubLabelId = null;
        this.addingSubLabelToId = null;
    }

    cancelSubLabelEdit(): void {
        this.editingSubLabelId = null;
    }

    saveEdit(labelId: string): void {
        this.isSaving = true;

        const keywords = this.editKeywordsRaw
            .split(',')
            .map(k => k.trim())
            .filter(k => k.length > 0);

        const payload: any = {
            name: this.editName.trim(),
            color: this.editColor,
            description: this.editDescription.trim() || null,
            keywords: keywords.length > 0 ? keywords : [],
            prompt_hint: this.editPromptHint.trim() || null,
        };

        this.smartLabelService.update(labelId, payload)
            .pipe(finalize(() => this.isSaving = false))
            .subscribe({
                next: (updated) => {
                    const idx = this.smartLabels.findIndex(l => l.id === labelId);
                    if (idx !== -1) {
                        this.smartLabels[idx] = { ...this.smartLabels[idx], ...updated };
                    }
                    this.editingLabelId = null;
                    this.editingSubLabelId = null;
                    this.showToast('Label updated successfully', 'success');
                },
                error: (err) => {
                    console.error('Failed to update label', err);
                    this.showToast(err.error?.detail || 'Failed to update', 'error');
                }
            });
    }

    saveSubLabelEdit(subLabelId: string): void {
        this.isSaving = true;

        const keywords = this.subEditKeywordsRaw
            .split(',')
            .map(k => k.trim())
            .filter(k => k.length > 0);

        const payload: any = {
            name: this.subEditName.trim(),
            color: this.subEditColor,
            description: this.subEditDescription.trim() || null,
            keywords: keywords.length > 0 ? keywords : [],
            prompt_hint: this.subEditPromptHint.trim() || null,
        };

        this.smartLabelService.update(subLabelId, payload)
            .pipe(finalize(() => this.isSaving = false))
            .subscribe({
                next: (updated) => {
                    for (const parent of this.smartLabels) {
                        if (parent.sub_labels) {
                            const idx = parent.sub_labels.findIndex(sl => sl.id === subLabelId);
                            if (idx !== -1) {
                                parent.sub_labels[idx] = { ...parent.sub_labels[idx], ...updated };
                                break;
                            }
                        }
                    }
                    this.editingSubLabelId = null;
                    this.showToast('Sub-category updated successfully', 'success');
                },
                error: (err) => {
                    console.error('Failed to update sub-label', err);
                    this.showToast(err.error?.detail || 'Failed to update', 'error');
                }
            });
    }

    private showToast(message: string, type: 'success' | 'error'): void {
        this.saveMessage = message;
        this.saveType = type;
        setTimeout(() => (this.saveMessage = ''), 3000);
    }
}
