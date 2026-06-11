import { describe, test, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

function jsonResponse(payload, status = 200) {
    return {
        ok: status >= 200 && status < 300,
        status,
        json: async () => payload,
    };
}

beforeEach(() => {
    const storePath = resolve(__dirname, '..', 'shared', 'param_store.js');
    const storeCode = readFileSync(storePath, 'utf-8');
    const loadStore = new Function(storeCode);
    loadStore();
    globalThis.fetch = vi.fn();
});

describe('SharedParamStore', () => {
    test('load merges base + computed values into canonical snapshot', async () => {
        globalThis.fetch
            .mockResolvedValueOnce(jsonResponse({
                parameters: [
                    { name: 'BP_1', value: '10' },
                    { name: 'bp_2', value: '2,5' },
                ],
            }))
            .mockResolvedValueOnce(jsonResponse({
                computed_parameters: [
                    { name: 'CP_1', value: '12.5' },
                ],
            }));

        const snapshot = await globalThis.SharedParamStore.load(123, {
            parameters: '/api/project/123/parameters/',
            computedParameters: '/api/project/123/computed-parameters/',
        });

        expect(snapshot).toEqual({
            bp_1: 10,
            bp_2: 2.5,
            cp_1: 12.5,
        });
        expect(globalThis.SharedParamStore.getSnapshot()).toEqual(snapshot);
    });

    test('refresh updates snapshot with latest server values', async () => {
        globalThis.fetch
            .mockResolvedValueOnce(jsonResponse({
                parameters: [{ name: 'bp_1', value: '10' }],
            }))
            .mockResolvedValueOnce(jsonResponse({
                computed_parameters: [{ name: 'cp_1', value: '20' }],
            }));

        await globalThis.SharedParamStore.load(222, {
            parameters: '/api/project/222/parameters/',
            computedParameters: '/api/project/222/computed-parameters/',
        });
        expect(globalThis.SharedParamStore.getSnapshot()).toEqual({ bp_1: 10, cp_1: 20 });

        globalThis.fetch
            .mockResolvedValueOnce(jsonResponse({
                parameters: [{ name: 'bp_1', value: '15' }],
            }))
            .mockResolvedValueOnce(jsonResponse({
                computed_parameters: [{ name: 'cp_1', value: '25' }],
            }));

        const refreshed = await globalThis.SharedParamStore.refresh();
        expect(refreshed).toEqual({ bp_1: 15, cp_1: 25 });
        expect(globalThis.SharedParamStore.getSnapshot()).toEqual({ bp_1: 15, cp_1: 25 });
        expect(globalThis.fetch).toHaveBeenCalledTimes(4);
    });
});
