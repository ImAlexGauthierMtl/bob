import { describe, expect, it, vi } from 'vitest';
import { of } from 'rxjs';

import { ChatService } from './chat.service';
import { BobService } from './bob.service';

describe('ChatService', () => {
    it('routes the conversation page through the Bob Chat converted agent chain', async () => {
        const bob = {
            chat: vi.fn().mockReturnValue(of({
                response: 'Bonjour depuis Bob.',
                session_id: 'chat_1',
                turn_count: 1,
                actions: [],
            })),
        } as unknown as BobService;
        const service = new ChatService(bob);

        const response = await new Promise<{ reply: string; sessionId: string }>((resolve) => {
            service.send('Salut Bob', 'chat_existing').subscribe(resolve);
        });

        expect(bob.chat).toHaveBeenCalledWith(
            'Salut Bob',
            'chat_existing',
            undefined,
            { source: 'conversation-page' },
            'workspace',
        );
        expect(response).toEqual({
            reply: 'Bonjour depuis Bob.',
            sessionId: 'chat_1',
        });
    });
});
