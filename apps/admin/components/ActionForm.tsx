'use client';

import { createContext, startTransition, useActionState, useContext, useEffect, useRef, type ReactNode } from 'react';
import type { ActionState } from '@/app/(admin)/actions';

type Action = (prev: ActionState, fd: FormData) => Promise<ActionState>;

const Pending = createContext(false);

/**
 * A form bound to a server action. Shows the API problem `detail` on failure and a status line on
 * success. A submit button with `data-confirm="…"` (or the form-level `confirm`) asks first.
 * Submission is dispatched manually so a failed attempt keeps what the user typed
 * (React resets forms after a form `action` completes).
 */
export function ActionForm({ action, children, className = '', confirm, resetOnSuccess, id }: {
  action: Action; children: ReactNode; className?: string; confirm?: string; resetOnSuccess?: boolean; id?: string;
}) {
  const [state, formAction, pending] = useActionState(action, {});
  const ref = useRef<HTMLFormElement>(null);
  const msgRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (state.ok && resetOnSuccess) ref.current?.reset();
    // A reason/note explains one change; never let it silently carry over to the next submission.
    if (state.ok) ref.current?.querySelectorAll<HTMLInputElement | HTMLTextAreaElement>('[name=reason],[name=note]').forEach((el) => { el.value = ''; });
    if (state.ok || state.error) msgRef.current?.focus();
  }, [state, resetOnSuccess]);

  function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const submitter = (e.nativeEvent as SubmitEvent).submitter as HTMLButtonElement | null;
    const msg = submitter?.dataset.confirm ?? confirm;
    if (msg && !window.confirm(msg)) return;
    const fd = new FormData(e.currentTarget, submitter);
    startTransition(() => formAction(fd));
  }

  return (
    <form ref={ref} id={id} action={formAction} onSubmit={onSubmit} className={className} aria-busy={pending}>
      <Pending.Provider value={pending}>{children}</Pending.Provider>
      <div ref={msgRef} tabIndex={-1} className="outline-none" aria-live="polite">
        {state.error && <p role="alert" className="mt-3 rounded-chip bg-danger-tint px-3 py-2 text-sm text-danger">{state.error}</p>}
        {state.ok && state.message && <p role="status" className="mt-3 rounded-chip bg-tint px-3 py-2 text-sm text-primary">{state.message}</p>}
      </div>
    </form>
  );
}

export function SubmitButton({ children, variant = 'primary', name, value, confirm, disabled, small }: {
  children: ReactNode; variant?: 'primary' | 'outline' | 'danger'; name?: string; value?: string; confirm?: string; disabled?: boolean; small?: boolean;
}) {
  const pending = useContext(Pending);
  return (
    <button type="submit" name={name} value={value} data-confirm={confirm} disabled={pending || disabled}
      className={`btn btn-${variant}${small ? ' btn-sm' : ''}`}>
      {pending ? 'অপেক্ষা করুন…' : children}
    </button>
  );
}

export function Field({ label, en, htmlFor, children, hint, required, className = '' }: {
  label: string; en?: string; htmlFor: string; children: ReactNode; hint?: ReactNode; required?: boolean; className?: string;
}) {
  return (
    <div className={className}>
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium">
        {label}{required && <span className="text-danger" aria-hidden> *</span>}
        {en && <span className="font-en ml-1 text-xs font-normal text-muted">· {en}</span>}
      </label>
      {children}
      {hint && <p id={`${htmlFor}-hint`} className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}
