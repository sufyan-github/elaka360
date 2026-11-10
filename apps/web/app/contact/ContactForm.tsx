'use client';

import { useId, useState, type FormEvent } from 'react';
import { CheckCircle2, Send } from 'lucide-react';
import { toBnDigits } from '@elaka360/shared';

const SUBJECT_MIN = 3;
const SUBJECT_MAX = 120;
const MESSAGE_MIN = 10;
const MESSAGE_MAX = 1000;
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type Status = { kind: 'idle' } | { kind: 'sending' } | { kind: 'sent' } | { kind: 'error'; message: string };

const inputCls =
  'mt-1 block w-full rounded-chip border border-line bg-surface px-3 py-2.5 text-[15px] text-ink placeholder:text-muted focus:border-secondary focus:outline-none aria-[invalid=true]:border-danger';

export function ContactForm() {
  const id = useId();
  const [subject, setSubject] = useState('');
  const [message, setMessage] = useState('');
  const [email, setEmail] = useState('');
  const [website, setWebsite] = useState(''); // honeypot
  const [status, setStatus] = useState<Status>({ kind: 'idle' });
  const [touched, setTouched] = useState(false);

  const s = subject.trim();
  const m = message.trim();
  const e = email.trim();
  const errors = {
    subject: s.length < SUBJECT_MIN ? `বিষয় অন্তত ${toBnDigits(SUBJECT_MIN)} অক্ষরের হতে হবে।` : null,
    message: m.length < MESSAGE_MIN ? `বার্তা অন্তত ${toBnDigits(MESSAGE_MIN)} অক্ষরের হতে হবে।` : null,
    email: e && !EMAIL_RE.test(e) ? 'ইমেইল ঠিকানাটি সঠিক মনে হচ্ছে না।' : null,
  };
  const invalid = Boolean(errors.subject || errors.message || errors.email);

  async function onSubmit(ev: FormEvent<HTMLFormElement>) {
    ev.preventDefault();
    setTouched(true);
    if (invalid || status.kind === 'sending') return;
    setStatus({ kind: 'sending' });
    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ subject: s, message: m, email: e || undefined, website }),
      });
      const data = (await res.json().catch(() => null)) as { ok?: boolean; error?: string } | null;
      if (res.ok && data?.ok) {
        setStatus({ kind: 'sent' });
        setSubject('');
        setMessage('');
        setEmail('');
        setTouched(false);
      } else {
        setStatus({ kind: 'error', message: data?.error ?? 'বার্তা পাঠানো যায়নি। কিছুক্ষণ পরে আবার চেষ্টা করুন।' });
      }
    } catch {
      setStatus({ kind: 'error', message: 'ইন্টারনেট সংযোগ নেই বা সার্ভারে পৌঁছানো যাচ্ছে না। সংযোগ দেখে আবার চেষ্টা করুন।' });
    }
  }

  if (status.kind === 'sent') {
    return (
      <div role="status" className="flex items-start gap-3 rounded-card border border-line bg-tint p-4">
        <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-verified" aria-hidden />
        <div>
          <p className="font-semibold">ধন্যবাদ, আপনার বার্তা পৌঁছেছে।</p>
          <p className="mt-1 text-sm text-muted">বার্তাগুলো পর্যালোচনা করা হয়, তবে সব বার্তার উত্তর দেওয়া সম্ভব না-ও হতে পারে।</p>
          <button type="button" onClick={() => setStatus({ kind: 'idle' })} className="mt-2 text-sm font-medium text-secondary underline underline-offset-2">
            আরেকটি বার্তা পাঠান
          </button>
        </div>
      </div>
    );
  }

  const show = (k: keyof typeof errors) => touched && errors[k];
  const count = message.length;

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4" aria-describedby={`${id}-note`}>
      <div>
        <label htmlFor={`${id}-subject`} className="text-sm font-semibold">
          বিষয় <span className="text-danger" aria-hidden>*</span>
        </label>
        <input
          id={`${id}-subject`}
          name="subject"
          required
          maxLength={SUBJECT_MAX}
          value={subject}
          onChange={(x) => setSubject(x.target.value)}
          aria-invalid={Boolean(show('subject'))}
          aria-describedby={show('subject') ? `${id}-subject-err` : undefined}
          className={inputCls}
          placeholder="যেমন: রাজশাহীর একটি তথ্যে ভুল"
        />
        {show('subject') && (
          <p id={`${id}-subject-err`} className="mt-1 text-sm text-danger">
            {errors.subject}
          </p>
        )}
      </div>

      <div>
        <label htmlFor={`${id}-message`} className="text-sm font-semibold">
          বার্তা <span className="text-danger" aria-hidden>*</span>
        </label>
        <textarea
          id={`${id}-message`}
          name="message"
          required
          rows={6}
          maxLength={MESSAGE_MAX}
          value={message}
          onChange={(x) => setMessage(x.target.value)}
          aria-invalid={Boolean(show('message'))}
          aria-describedby={`${id}-count${show('message') ? ` ${id}-message-err` : ''}`}
          className={`${inputCls} resize-y`}
          placeholder="কোন পাতায়, কী সমস্যা বা প্রস্তাব — বিস্তারিত লিখুন। কোনো তথ্য সংশোধনের জন্য উৎসের লিংক দিলে ভালো হয়।"
        />
        <div className="mt-1 flex items-start justify-between gap-3 text-sm">
          <span id={`${id}-message-err`} className="text-danger">
            {show('message') ? errors.message : ''}
          </span>
          <span id={`${id}-count`} className={`shrink-0 tabular-nums ${count >= MESSAGE_MAX ? 'text-danger' : 'text-muted'}`} aria-live="polite">
            {toBnDigits(count)}/{toBnDigits(MESSAGE_MAX)}
            <span className="sr-only"> অক্ষর</span>
          </span>
        </div>
      </div>

      <div>
        <label htmlFor={`${id}-email`} className="text-sm font-semibold">
          ইমেইল <span className="font-normal text-muted">(ঐচ্ছিক)</span>
        </label>
        <input
          id={`${id}-email`}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          maxLength={120}
          value={email}
          onChange={(x) => setEmail(x.target.value)}
          aria-invalid={Boolean(show('email'))}
          aria-describedby={`${id}-email-hint${show('email') ? ` ${id}-email-err` : ''}`}
          className={`${inputCls} font-en`}
        />
        <p id={`${id}-email-hint`} className="mt-1 text-xs text-muted">
          উত্তর পেতে চাইলে দিন। এটি শুধু এই বার্তার উত্তর দেওয়ার জন্য ব্যবহার করা হবে।
        </p>
        {show('email') && (
          <p id={`${id}-email-err`} className="mt-1 text-sm text-danger">
            {errors.email}
          </p>
        )}
      </div>

      {/* Honeypot: hidden from people and assistive technology; bots that fill every field are dropped by the API. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label htmlFor={`${id}-website`}>এই ঘরটি খালি রাখুন</label>
        <input id={`${id}-website`} name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(x) => setWebsite(x.target.value)} />
      </div>

      {status.kind === 'error' && (
        <p role="alert" className="rounded-chip border border-danger bg-danger-tint px-3 py-2 text-sm text-ink">
          {status.message}
        </p>
      )}

      <p id={`${id}-note`} className="text-xs text-muted">
        জরুরি প্রয়োজনে এই ফর্ম নয় — <a href="tel:999" className="font-semibold text-danger underline">{toBnDigits('999')}</a> নম্বরে কল করুন।
      </p>

      <button
        type="submit"
        disabled={status.kind === 'sending'}
        className="inline-flex w-full items-center justify-center gap-2 rounded-chip bg-primary px-4 py-3 font-semibold text-on-primary hover:bg-primary-hover disabled:opacity-60 sm:w-auto"
      >
        <Send className="h-4 w-4" aria-hidden />
        {status.kind === 'sending' ? 'পাঠানো হচ্ছে…' : 'বার্তা পাঠান'}
      </button>
    </form>
  );
}
