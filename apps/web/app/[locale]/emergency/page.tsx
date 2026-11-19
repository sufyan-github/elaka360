import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Flame, HeartPulse, MapPin, Phone, ShieldAlert, Siren } from 'lucide-react';
import type { EmergencyNumber } from '@elaka360/shared';
import { nameOf } from '@elaka360/shared';
import { api } from '@/lib/api';
import { asLocale, digits, evidenceText, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';
import fallback from '@/public/data/hotlines.json';

/**
 * Must work when the API is down (finding C2): statically rendered, revalidated hourly, and falls back to
 * the hotline list bundled at build time from the seed (only numbers with official/secondary evidence).
 */
export const revalidate = 3600;

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Emergency' });
  return { title: t('title'), alternates: localeAlternates(locale, '/emergency') };
}

async function hotlines(): Promise<{ items: Pick<EmergencyNumber, 'number' | 'name_bn' | 'name_en' | 'category' | 'evidence_level' | 'notes'>[]; live: boolean }> {
  try {
    return { items: await api.emergency(), live: true };
  } catch {
    return { items: fallback as EmergencyNumber[], live: false };
  }
}

const QUICK = [
  { label: 'police', sub: '999', tel: '999', Icon: ShieldAlert },
  { label: 'fire', sub: '102 / 999', tel: '102', Icon: Flame },
  { label: 'ambulance', sub: '999', tel: '999', Icon: HeartPulse },
] as const;

export default async function EmergencyPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Emergency');
  const { items, live } = await hotlines();
  const hasFire = items.some((n) => n.number === '102');
  return (
    <>
      <section className="hero-red -mx-4 mt-0 px-4 py-6 md:mx-0 md:mt-4 md:rounded-card md:px-8">
        <h1 className="flex items-center gap-2 text-2xl font-bold">
          <Siren className="h-7 w-7" aria-hidden /> {t('title')}
        </h1>
        <p className="mt-1 text-sm text-white/90">{t('intro')}</p>
        <a href="tel:999" className="mt-4 flex items-center justify-between rounded-card bg-white px-4 py-4 text-[#b51d1d] shadow-card">
          <span className="flex items-center gap-2 text-lg font-semibold">
            <Phone className="h-7 w-7" aria-hidden /> {t('call999')}
          </span>
          <span className="font-en text-4xl font-bold">999</span>
        </a>
      </section>

      <div className="mt-4 grid grid-cols-3 gap-3">
        {QUICK.filter((q) => q.tel === '999' || hasFire).map(({ label, sub, tel, Icon }) => (
          <a key={label} href={`tel:${tel}`} className="flex flex-col items-center gap-1 rounded-card border border-line bg-surface p-3 text-center shadow-card">
            <Icon className="h-7 w-7 text-danger" aria-hidden />
            <span className="text-sm font-semibold">{t(label)}</span>
            <span className="text-xs text-muted">{digits(sub, locale)}</span>
          </a>
        ))}
      </div>

      <Link href="/near-me?category=emergency" className="mt-3 flex items-center gap-2 rounded-card border border-line bg-surface px-4 py-3 font-semibold">
        <MapPin className="h-5 w-5 text-danger" aria-hidden /> {t('nearby')}
      </Link>

      <Section title={t('hotlines')}>
        <Card className="divide-y divide-line">
          {items.map((n) => (
            <a key={n.number} href={`tel:${n.number}`} className="flex items-center gap-3 px-4 py-3">
              <span className="w-20 text-xl font-bold text-danger">{digits(n.number, locale)}</span>
              <span className="min-w-0 flex-1">
                <span className="block font-semibold">{nameOf(n, locale)}</span>
                <span lang={otherLocale(locale)} className={`block text-xs text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{nameOf(n, otherLocale(locale))}</span>
                {n.notes && <span className="block text-[11px] text-muted">{n.notes}</span>}
              </span>
              <span className="grid h-10 w-10 place-items-center rounded-full bg-secondary text-on-primary" aria-hidden>
                <Phone className="h-5 w-5" />
              </span>
            </a>
          ))}
        </Card>
        <p className="mt-2 text-xs text-muted">
          {t('note', { label: evidenceText('secondary', locale).label })}
          {!live && ` ${t('offlineList')}`}
        </p>
      </Section>
    </>
  );
}
