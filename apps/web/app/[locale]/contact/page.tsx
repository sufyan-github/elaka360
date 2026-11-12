import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Phone } from 'lucide-react';
import { asLocale, digits, evidenceText, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';
import { ContactForm } from './ContactForm';

export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Contact' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/contact') };
}

const FAQ = ['accuracy', 'report', 'add', 'data'] as const;
const linkCls = 'font-medium text-secondary underline';

export default async function ContactPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Contact');
  const tags = {
    policy: (c: React.ReactNode) => <Link href="/data-policy" className={linkCls}>{c}</Link>,
    contribute: (c: React.ReactNode) => <Link href="/contribute" className={linkCls}>{c}</Link>,
    guidelines: (c: React.ReactNode) => <Link href="/guidelines" className={linkCls}>{c}</Link>,
    privacy: (c: React.ReactNode) => <Link href="/privacy" className={linkCls}>{c}</Link>,
    label: evidenceText('secondary', locale).label,
  };
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>

      <a href="tel:999" className="mt-4 flex items-center gap-3 rounded-card border border-danger bg-danger-tint px-4 py-3 text-ink">
        <Phone className="h-5 w-5 shrink-0 text-danger" aria-hidden />
        <span className="text-sm">
          {t.rich('emergency', {
            strong: (c) => <strong>{c}</strong>,
            num: (c) => <span className="font-bold text-danger">{c}</span>,
            number: digits('999', locale),
          })}
        </span>
      </a>

      <Section title={t('formTitle')}>
        <Card className="p-4">
          <p className="mb-4 text-sm text-muted">{t('formIntro')}</p>
          <ContactForm />
        </Card>
      </Section>

      <Section title={t('faqTitle')}>
        <Card className="divide-y divide-line">
          {FAQ.map((k) => (
            <details key={k} className="group px-4 py-3">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-3 font-semibold [&::-webkit-details-marker]:hidden">
                <h3 className="text-[15px]">{t(`faq.${k}.q`)}</h3>
                <span className="text-lg leading-none text-muted transition-transform group-open:rotate-45 motion-reduce:transition-none" aria-hidden>
                  +
                </span>
              </summary>
              <p className="mt-2 text-sm">{t.rich(`faq.${k}.a`, tags)}</p>
            </details>
          ))}
        </Card>
      </Section>
    </div>
  );
}
