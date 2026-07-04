import { Component, OnInit, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
    BobAssistantSettingsService,
    BobMemorySettingsResponse,
    KnowledgeCollection,
    KnowledgeDatabase,
    KnowledgeOverviewResponse,
    KnowledgeSource,
} from '../../../shared/services/bob-assistant-settings.service';

@Component({
    selector: 'croo-settings-knowledge',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './settings-knowledge.html',
    styleUrl: './settings-knowledge.css',
})
export class SettingsKnowledgeComponent implements OnInit {
    private settings = inject(BobAssistantSettingsService);

    loading = true;
    saving = false;
    error: string | null = null;
    memory: BobMemorySettingsResponse | null = null;
    knowledge: KnowledgeOverviewResponse | null = null;

    databaseForm = {
        name: 'bob_support_knowledge',
        display_name: 'Bob Support Knowledge',
        description: 'Support technique et service a la clientele issus de Zoho Desk.',
        milvus_database: 'bob_knowledge',
        embedding_provider: 'fireworks',
        embedding_model: 'fireworks/qwen3-embedding-8b',
        embedding_dimension: 4096,
    };

    collectionForm = {
        database_id: '',
        name: 'zoho_support_procedures',
        display_name: 'Zoho Support Procedures',
        theme: 'support_technique',
        description: 'Procedures candidates extraites des tickets Zoho Desk.',
        milvus_collection: 'support_procedure_chunks_v1',
        scope_type: 'organization',
        source_kind: 'zoho_desk',
    };

    sourceForm = {
        collection_id: '',
        name: 'Zoho Desk - Support tickets',
        provider: 'pipedream',
        source_type: 'zoho_desk',
        pipedream_app: 'zoho_desk',
        pipedream_source_id: '',
        sync_mode: 'incremental',
        ingestion_strategy: 'tickets_to_candidate_procedures',
    };

    ngOnInit(): void {
        this.reload();
    }

    reload(): void {
        this.loading = true;
        this.error = null;
        this.settings.getMemory().subscribe({
            next: (memory) => {
                this.memory = memory;
                this.settings.getKnowledge().subscribe({
                    next: (knowledge) => {
                        this.knowledge = knowledge;
                        this.hydrateDefaults();
                        this.loading = false;
                    },
                    error: () => this.fail('Knowledge is unavailable'),
                });
            },
            error: () => this.fail('Memory settings are unavailable'),
        });
    }

    createDatabase(): void {
        this.saving = true;
        this.settings.createKnowledgeDatabase(this.databaseForm).subscribe({
            next: () => this.reloadAfterSave(),
            error: () => this.fail('Database could not be created'),
        });
    }

    createCollection(): void {
        this.saving = true;
        this.settings.createKnowledgeCollection(this.collectionForm).subscribe({
            next: () => this.reloadAfterSave(),
            error: () => this.fail('Collection could not be created'),
        });
    }

    createSource(): void {
        this.saving = true;
        const payload = {
            ...this.sourceForm,
            pipedream_source_id: this.sourceForm.pipedream_source_id || null,
        };
        this.settings.createKnowledgeSource(payload).subscribe({
            next: () => this.reloadAfterSave(),
            error: () => this.fail('Source could not be created'),
        });
    }

    trackDatabase(_: number, item: KnowledgeDatabase): string {
        return item.id;
    }

    trackCollection(_: number, item: KnowledgeCollection): string {
        return item.id;
    }

    trackSource(_: number, item: KnowledgeSource): string {
        return item.id;
    }

    private hydrateDefaults(): void {
        const database = this.knowledge?.databases[0];
        const collection = this.knowledge?.collections[0];
        if (database) {
            this.collectionForm.database_id = database.id;
        }
        if (collection) {
            this.sourceForm.collection_id = collection.id;
        }
    }

    private reloadAfterSave(): void {
        this.saving = false;
        this.reload();
    }

    private fail(message: string): void {
        this.error = message;
        this.loading = false;
        this.saving = false;
    }
}
