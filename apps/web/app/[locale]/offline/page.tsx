import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Phone, Siren, WifiOff } from 'lucide-react';
import { nameOf, type EvidenceLevel } from '@elaka360/shared';
import { asLocale, digits, evidenceText, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';
import hotlinesJson from '@/public/data/hotlines.json';

// Pre-rendered at build time (no API call) so the service worker can cache it as the offline fallback
// (/offline for Bangla, /en/offline for English).
export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Offline' });
  return { title: t('metaTitle'), robots: { index: false }, alternates: localeAlternates(locale, '/offline') };
}

type Hotline = { number: string; name_bn: string; name_en: string; evidence_level: EvidenceLevel };
const hotlines = hotlinesJson as Hotline[];

export default async function OfflinePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Offline');
  const secondary = evidenceText('secondary', locale);
  return (
    <div className="pt-6">
      <h1 className="flex items-center gap-2 text-2xl font-bold">
        <WifiOff className="h-7 w-7 text-muted" aria-hidden /> {t('title')}
      </h1>
      <p className="mt-2 text-[15px]">{t('body')}</p>
      <p lang={otherLocale(locale)} className={`mt-1 text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('bodyOther')}</p>

      <Link href="/emergency" className="mt-4 flex items-center justify-between rounded-card bg-danger px-4 py-3 font-semibold text-on-danger shadow-card">
        <span className="flex items-center gap-2">
          <Siren className="h-5 w-5" aria-hidden /> {t('openEmergency')}
        </span>
        <span aria-hidden>→</span>
      </Link>

      <Section title={t('hotlines')}>
        <p className="mb-3 text-sm">
          {t.rich('call999', { strong: (c) => <strong>{c}</strong>, number: digits('999', locale) })}
        </p>
        <Card className="divide-y divide-line">
          {hotlines.map((h) => (
            <a key={h.number} href={`tel:${h.number}`} className="flex items-center gap-3 px-4 py-3">
              <span className="w-16 shrink-0 text-xl font-bold text-danger">{digits(h.number, locale)}</span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{nameOf(h, locale)}</span>
                <span lang={otherLocale(locale)} className={`block text-xs text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{nameOf(h, otherLocale(locale))}</span>
                <span className="block text-[11px] text-muted">{evidenceText(h.evidence_level, locale).label}</span>
              </span>
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-primary text-on-primary" aria-hidden>
                <Phone className="h-5 w-5" />
              </span>
              <span className="sr-only">{t('callSr')}</span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">
          {hotlines.every((h) => h.evidence_level === 'secondary')
            ? t('allSecondary', { label: secondary.label, hint: secondary.hint })
            : t('mixed')}{' '}
          {t('bundled')}
        </p>
      </Section>
    </div>
  );
}
