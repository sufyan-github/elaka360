import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { Check, X } from 'lucide-react';
import { asLocale, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Guidelines' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/guidelines') };
}

const RULES = ['source', 'personal', 'spam', 'photos', 'respect'] as const;
const REJECTED = ['r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7'] as const;

export default async function GuidelinesPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Guidelines');
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>
      <p className="mt-3 text-[15px]">{t('intro')}</p>

      <Section title={t('rulesTitle')}>
        <Card className="divide-y divide-line">
          {RULES.map((k) => (
            <div key={k} className="flex gap-3 px-4 py-3">
              <Check className="mt-1 h-5 w-5 shrink-0 text-verified" aria-hidden />
              <div>
                <h3 className="font-semibold">{t(`rules.${k}.title`)}</h3>
                <p className="mt-0.5 text-sm">{t(`rules.${k}.body`)}</p>
              </div>
            </div>
          ))}
        </Card>
      </Section>

      <Section title={t('rejectedTitle')}>
        <Card className="p-4">
          <ul className="space-y-1.5 text-[15px]">
            {REJECTED.map((k) => (
              <li key={k} className="flex gap-2">
                <X className="mt-1 h-4 w-4 shrink-0 text-danger" aria-hidden />
                <span>{t(`rejected.${k}`)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </Section>

      <Section title={t('afterTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t.rich('after1', { link: (c) => <Link href="/data-policy" className="font-medium text-secondary underline">{c}</Link> })}</p>
          <p>{t('after2')}</p>
          <p>{t('after3')}</p>
        </Card>
      </Section>

      <div className="mt-6 flex flex-col gap-2 sm:flex-row">
        <Link href="/contribute" className="inline-flex items-center justify-center rounded-chip bg-primary px-4 py-3 font-semibold text-on-primary hover:bg-primary-hover">
          {t('ctaContribute')}
        </Link>
        <Link href="/terms" className="inline-flex items-center justify-center rounded-chip border border-line bg-surface px-4 py-3 font-semibold text-ink">
          {t('ctaTerms')}
        </Link>
      </div>
    </div>
  );
}
