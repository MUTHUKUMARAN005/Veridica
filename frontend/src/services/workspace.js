import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { freshState } from './preview';
const storageKey = 'veridica.frontend-preview.v1';
const Context = createContext(null);
function loadState() {
    try {
        const stored = JSON.parse(localStorage.getItem(storageKey) ?? 'null');
        if (stored?.schema === 1 && ['ideas', 'reviews', 'evolutions', 'assignments', 'audit'].every((key) => Array.isArray(stored.state?.[key])) && stored.state.ideas.every((idea) => typeof idea.title === 'string' && Array.isArray(idea.features)))
            return { ...stored.state, comments: Array.isArray(stored.state.comments) ? stored.state.comments : [], signals: Array.isArray(stored.state.signals) ? stored.state.signals : [], assessments: Array.isArray(stored.state.assessments) ? stored.state.assessments : [] };
    }
    catch {
        return freshState();
    }
    return freshState();
}
export function WorkspaceProvider({ children }) {
    const [state, setState] = useState(loadState);
    const currentState = useRef(state);
    const [role, setRole] = useState(() => {
        try {
            const stored = sessionStorage.getItem('veridica.preview-role');
            return stored === 'reviewer' || stored === 'admin' ? stored : 'owner';
        }
        catch {
            return 'owner';
        }
    });
    const [toast, notify] = useState('');
    useEffect(() => {
        try {
            sessionStorage.setItem('veridica.preview-role', role);
        }
        catch {
            return;
        }
    }, [role]);
    useEffect(() => {
        try {
            localStorage.setItem(storageKey, JSON.stringify({ schema: 1, state }));
        }
        catch {
            notify('Browser storage is unavailable. Changes will last only for this session.');
        }
    }, [state]);
    useEffect(() => {
        if (!toast)
            return;
        const timeout = window.setTimeout(() => notify(''), 5000);
        return () => window.clearTimeout(timeout);
    }, [toast]);
    const update = useCallback((transform, message) => {
        try {
            const next = transform(currentState.current);
            currentState.current = next;
            setState(next);
            if (message)
                notify(message);
        }
        catch (error) {
            notify(error instanceof Error ? error.message : 'Unable to update preview.');
        }
    }, [notify]);
    const reset = useCallback(() => {
        const next = freshState();
        currentState.current = next;
        setState(next);
        try {
            localStorage.removeItem('veridica.saved-ideas.v1');
        }
        catch {
            notify('Sample records restored, but browser storage could not clear saved ideas.');
            return;
        }
        notify('Sample workspace restored.');
    }, [notify]);
    return <Context.Provider value={{ state, update, role, setRole, toast, notify, reset }}>{children}</Context.Provider>;
}
export function useWorkspace() {
    const context = useContext(Context);
    if (!context)
        throw new Error('Workspace provider is required.');
    return context;
}
