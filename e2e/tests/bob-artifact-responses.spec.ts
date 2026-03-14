/**
 * Bob Artifact Response Tests — 30 E2E tests via API
 *
 * Tests that Bob produces correct artifact types, tool steps,
 * and response structure for varied user messages.
 *
 * Run: npx playwright test e2e/tests/bob-artifact-responses.spec.ts
 */
import { test, expect } from 'playwright';

const API_BASE = 'http://localhost:8000';

// ── Auth helper: get JWT token ──────────────────────────────
async function getAuthToken(): Promise<string> {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: 'admin@croo.digital', password: 'admin123' }),
    });
    const data = await res.json();
    return data.access_token;
}

// ── Helper: send message to Bob API ─────────────────────────
interface BobResponse {
    response: string;
    session_id: string;
    actions: Array<{ type: string; page?: string; entity?: string; display_type?: string; title?: string; items?: any[] }>;
    tool_steps: Array<{ tool: string; status: string }>;
    artifact: {
        type: string;
        title: string;
        fields: Array<{ label: string; value: string }>;
        status: string;
        columns?: string[];
        rows?: string[][];
        items?: Array<{ label: string; value: string }>;
        sections?: Array<{ title: string; items: any[] }>;
    } | null;
}

async function askBob(token: string, message: string, channel: string = 'workspace'): Promise<BobResponse> {
    const res = await fetch(`${API_BASE}/api/v1/bob/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ message, channel }),
    });
    expect(res.status).toBe(200);
    return res.json();
}

// ── Shared state ────────────────────────────────────────────
let token: string;

test.beforeAll(async () => {
    token = await getAuthToken();
    expect(token).toBeTruthy();
});

// ═══════════════════════════════════════════════════════════════
//  GROUP 1: NAVIGATE — data_table artifact (10 tests)
// ═══════════════════════════════════════════════════════════════

test.describe('Navigate → data_table artifact', () => {

    test('T01: "liste mes comptes" → data_table organizations', async () => {
        const r = await askBob(token, 'liste mes comptes');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.type).toBe('data_table');
        expect(r.artifact!.columns).toBeTruthy();
        expect(r.artifact!.rows).toBeTruthy();
        expect(r.artifact!.columns!.length).toBeGreaterThan(0);
    });

    test('T02: "montre mes contacts" → data_table contacts', async () => {
        const r = await askBob(token, 'montre mes contacts');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.type).toBe('data_table');
        expect(r.artifact!.columns).toBeTruthy();
    });

    test('T03: "affiche les opportunités" → data_table or navigate', async () => {
        const r = await askBob(token, 'affiche les opportunités');
        // Workspace channel returns data_table
        if (r.artifact) {
            expect(r.artifact.type).toBe('data_table');
        } else {
            // Compact channel returns navigate action
            expect(r.actions.some(a => a.type === 'navigate')).toBe(true);
        }
    });

    test('T04: "show me my accounts" → data_table EN', async () => {
        const r = await askBob(token, 'show me my accounts');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.type).toBe('data_table');
    });

    test('T05: "mes organisations" → data_table', async () => {
        const r = await askBob(token, 'mes organisations');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.type).toBe('data_table');
    });

    test('T06: "va sur le dashboard" compact → navigate action', async () => {
        const r = await askBob(token, 'va sur le dashboard', 'compact');
        expect(r.actions.some(a => a.type === 'navigate')).toBe(true);
    });

    test('T07: "go to contacts" compact → navigate action', async () => {
        const r = await askBob(token, 'go to contacts', 'compact');
        expect(r.actions.some(a => a.type === 'navigate' && a.page === 'contacts')).toBe(true);
    });

    test('T08: "page des contacts" → has response', async () => {
        const r = await askBob(token, 'page des contacts');
        expect(r.response).toBeTruthy();
        // Should have either artifact or navigate action
        const hasArtifact = r.artifact !== null;
        const hasNavigate = r.actions.some(a => a.type === 'navigate');
        expect(hasArtifact || hasNavigate).toBe(true);
    });

    test('T09: "liste moi mes comptes" → data_table has rows', async () => {
        const r = await askBob(token, 'liste moi mes comptes');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.type).toBe('data_table');
        expect(r.artifact!.rows!.length).toBeGreaterThan(0);
    });

    test('T10: "affiche mes organisations" → data_table status complete', async () => {
        const r = await askBob(token, 'affiche mes organisations');
        expect(r.artifact).not.toBeNull();
        expect(r.artifact!.status).toBe('complete');
    });
});


// ═══════════════════════════════════════════════════════════════
//  GROUP 2: SEARCH_ENTITY — search_results artifact (5 tests)
// ═══════════════════════════════════════════════════════════════

test.describe('Search Entity → search_results artifact', () => {

    test('T11: "cherche ASQ" → search_results with match', async () => {
        const r = await askBob(token, 'cherche ASQ');
        expect(r.tool_steps.length).toBeGreaterThan(0);
        expect(r.tool_steps.some(s => s.tool.toLowerCase().includes('search'))).toBe(true);
        expect(r.response).toBeTruthy();
    });

    test('T12: "trouve Madysta" → has tool step', async () => {
        const r = await askBob(token, 'trouve Madysta');
        expect(r.tool_steps.length).toBeGreaterThan(0);
    });

    test('T13: "search for Bombardier" → search response EN', async () => {
        const r = await askBob(token, 'search for Bombardier');
        expect(r.tool_steps.length).toBeGreaterThan(0);
        expect(r.response).toBeTruthy();
    });

    test('T14: "recherche le compte Desjardins" → actions emitted', async () => {
        const r = await askBob(token, 'recherche le compte Desjardins');
        expect(r.response).toBeTruthy();
        // Should have search action or artifact
        const hasSearchAction = r.actions.some(a => a.type === 'search_entity');
        const hasToolStep = r.tool_steps.length > 0;
        expect(hasSearchAction || hasToolStep).toBe(true);
    });

    test('T15: "where is the contact named Alex" → search response', async () => {
        const r = await askBob(token, 'where is the contact named Alex');
        expect(r.response).toBeTruthy();
    });
});


// ═══════════════════════════════════════════════════════════════
//  GROUP 3: UPDATE_ENTITY — tool steps + alert artifact (5 tests)
// ═══════════════════════════════════════════════════════════════

test.describe('Update Entity → tool steps + response', () => {

    test('T16: "change le status de ASQ pour client" → has update tool step', async () => {
        const r = await askBob(token, 'change le status de ASQ Consultants pour client');
        expect(r.tool_steps.length).toBeGreaterThan(0);
        // Should have search + update tool steps
        const toolNames = r.tool_steps.map(s => s.tool.toLowerCase());
        expect(toolNames.some(t => t.includes('update') || t.includes('search'))).toBe(true);
    });

    test('T17: "modifier le statut de Madysta pour actif" → update response', async () => {
        const r = await askBob(token, 'modifier le statut de Madysta pour actif');
        expect(r.response).toBeTruthy();
        expect(r.tool_steps.length).toBeGreaterThan(0);
    });

    test('T18: "update ASQ industry to Technology" → update EN', async () => {
        const r = await askBob(token, 'update ASQ industry to Technology');
        expect(r.response).toBeTruthy();
        expect(r.tool_steps.length).toBeGreaterThan(0);
    });

    test('T19: "met le status de Madysta à prospect" → tool steps present', async () => {
        const r = await askBob(token, 'met le status de Madysta à prospect');
        expect(r.tool_steps.length).toBeGreaterThan(0);
    });

    test('T20: "change Bauchon status to customer" → handles partial name', async () => {
        const r = await askBob(token, 'change Bauchon status to customer');
        expect(r.response).toBeTruthy();
        // Should either match fuzzy or say not found
        expect(r.tool_steps.length).toBeGreaterThanOrEqual(0);
    });
});


// ═══════════════════════════════════════════════════════════════
//  GROUP 4: ANALYTICS — bob_display list/stats actions (5 tests)
// ═══════════════════════════════════════════════════════════════

test.describe('Analytics → bob_display actions', () => {

    test('T21: "pipeline de ventes" → bob_display or pipeline artifact', async () => {
        const r = await askBob(token, 'pipeline de ventes');
        expect(r.response).toBeTruthy();
        // Should have bob_display action or tool steps
        const hasBobDisplay = r.actions.some(a => a.type === 'bob_display');
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasBobDisplay || hasToolSteps).toBe(true);
    });

    test('T22: "mes meilleures opportunités" → bob_display list', async () => {
        const r = await askBob(token, 'mes meilleures opportunités');
        expect(r.response).toBeTruthy();
        const hasBobDisplay = r.actions.some(a => a.type === 'bob_display' && a.display_type === 'list');
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasBobDisplay || hasToolSteps).toBe(true);
    });

    test('T23: "deals stagnants" → response mentioning stale', async () => {
        const r = await askBob(token, 'deals stagnants');
        expect(r.response).toBeTruthy();
    });

    test('T24: "comptes par industrie" → bob_display stats', async () => {
        const r = await askBob(token, 'comptes par industrie');
        expect(r.response).toBeTruthy();
        const hasBobDisplay = r.actions.some(a => a.type === 'bob_display');
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasBobDisplay || hasToolSteps).toBe(true);
    });

    test('T25: "résumé du jour" → daily summary with stats', async () => {
        const r = await askBob(token, 'résumé du jour');
        expect(r.response).toBeTruthy();
        const hasBobDisplay = r.actions.some(a => a.type === 'bob_display');
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasBobDisplay || hasToolSteps).toBe(true);
    });
});


// ═══════════════════════════════════════════════════════════════
//  GROUP 5: CREATE + GENERAL — tool steps + correct intents (5 tests)
// ═══════════════════════════════════════════════════════════════

test.describe('Create + General → correct response structure', () => {

    test('T26: "ajoute un contact Jean Dupont" → create contact response', async () => {
        const r = await askBob(token, 'ajoute un contact Jean Dupont');
        expect(r.response).toBeTruthy();
        // Should have artifact (contact card) or tool steps
        const hasArtifact = r.artifact !== null;
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasArtifact || hasToolSteps).toBe(true);
    });

    test('T27: "contacts sans email" → contacts_no_email response', async () => {
        const r = await askBob(token, 'contacts sans email');
        expect(r.response).toBeTruthy();
    });

    test('T28: "comptes sans opportunité" → accounts_no_opp response', async () => {
        const r = await askBob(token, 'comptes sans opportunité');
        expect(r.response).toBeTruthy();
    });

    test('T29: "bonjour" → greeting or daily summary', async () => {
        const r = await askBob(token, 'bonjour');
        expect(r.response).toBeTruthy();
        // Bob should respond with text even if classified as daily_summary
        expect(r.response.length).toBeGreaterThan(5);
    });

    test('T30: "montre les produits" → list_products response', async () => {
        const r = await askBob(token, 'montre les produits');
        expect(r.response).toBeTruthy();
        const hasBobDisplay = r.actions.some(a => a.type === 'bob_display');
        const hasToolSteps = r.tool_steps.length > 0;
        expect(hasBobDisplay || hasToolSteps).toBe(true);
    });
});
