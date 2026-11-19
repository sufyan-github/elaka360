import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { asLocale, evidenceText, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'About' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/about') };
}

const LEVELS = ['official', 'secondary', 'community', 'unverified'] as const;
const PLAN = ['plan1', 'plan2', 'plan3', 'plan4'] as const;
const MORE = [
  { href: '/data-policy', key: 'dataPolicy' },
  { href: '/guidelines', key: 'guidelines' },
  { href: '/contribute', key: 'contribute' },
  { href: '/contact', key: 'contact' },
] as const;

export default async function AboutPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('About');
  const strong = (c: React.ReactNode) => <strong>{c}</strong>;
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>

      <Section title={t('missionTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t('mission1')}</p>
          <p>{t('mission2')}</p>
          <p className="text-sm text-muted">{t('independent')}</p>
        </Card>
      </Section>

      <Section title={t('howTitle')}>
        <Card className="space-y-3 p-4 text-[15px]">
          <p>{t('howIntro')}</p>
          <ul className="space-y-1.5">
            {LEVELS.map((k) => (
              <li key={k} className="flex flex-wrap items-baseline gap-x-2">
                <span className="rounded-full bg-tint px-2 py-0.5 text-xs font-medium text-primary">{evidenceText(k, locale).label}</span>
                <span className="text-sm text-muted">{evidenceText(k, locale).hint}</span>
              </li>
            ))}
          </ul>
          <p>{t.rich('howSourced', { strong, official: evidenceText('official', locale).label, secondary: evidenceText('secondary', locale).label })}</p>
          <p>{t('howSecondary')}</p>
          <p>{t('howCommunity')}</p>
          <p>{t.rich('howPilot', { strong })}</p>
        </Card>
      </Section>

      <Section title={t('planTitle')}>
        <Card className="p-4 text-[15px]">
          <p className="mb-2 text-sm text-muted">{t('planIntro')}</p>
          <ul className="list-disc space-y-1.5 pl-5">
            {PLAN.map((k) => <li key={k}>{t(k)}</li>)}
          </ul>
        </Card>
      </Section>

      <Section title={t('moreTitle')}>
        <Card className="divide-y divide-line">
          {MORE.map((l) => (
            <Link key={l.href} href={l.href} className="block px-4 py-3 hover:bg-tint">
              <span className="block font-semibold text-primary">{t(`more.${l.key}.label`)}</span>
              <span className="block text-sm text-muted">{t(`more.${l.key}.sub`)}</span>
            </Link>
          ))}
        </Card>
      </Section>
    </div>
  );
}
