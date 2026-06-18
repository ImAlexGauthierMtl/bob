export interface RemoteState<T> {
    data: T | null;
    loading: boolean;
    error: string | null;
}

export function initialRemoteState<T>(): RemoteState<T> {
    return {
        data: null,
        loading: false,
        error: null,
    };
}

export function errorMessage(error: unknown): string {
    if (error instanceof Error) {
        return error.message;
    }
    return 'Request failed';
}
