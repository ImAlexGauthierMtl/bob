import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { UserToolAccessResponse, UserToolPreferences } from '../../../shared/models/tool-governance.model';
import { ToolGovernanceService } from '../../../shared/services/tool-governance.service';

@Component({
    selector: 'croo-settings-my-tools',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink],
    templateUrl: './settings-my-tools.html',
    styleUrls: ['../settings-shared.css', './settings-my-tools.css'],
})
export class SettingsMyToolsComponent implements OnInit {
    private toolGovernance = inject(ToolGovernanceService);

    access: UserToolAccessResponse | null = null;
    preferences: UserToolPreferences = {
        preferred_email_provider: 'auto',
        preferred_calendar_provider: 'auto',
        require_write_confirmation: true,
        show_tool_trace: true,
        allow_personal_connectors: true,
    };
    loading = false;
    saving = false;
    error: string | null = null;
    success: string | null = null;

    ngOnInit(): void {
        this.load();
    }

    load(): void {
        this.loading = true;
        this.error = null;
        this.toolGovernance.getMyAccess().subscribe({
            next: (access) => {
                this.access = access;
                this.preferences = { ...access.preferences };
                this.loading = false;
            },
            error: () => {
                this.error = 'Unable to load your Bob tool settings.';
                this.loading = false;
            },
        });
    }

    savePreferences(): void {
        this.saving = true;
        this.success = null;
        this.error = null;
        this.toolGovernance.updateMyPreferences(this.preferences).subscribe({
            next: (preferences) => {
                this.preferences = preferences;
                if (this.access) {
                    this.access = { ...this.access, preferences };
                }
                this.success = 'Preferences saved.';
                this.saving = false;
            },
            error: () => {
                this.error = 'Unable to save your preferences.';
                this.saving = false;
            },
        });
    }

}
