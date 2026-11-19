import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { asLocale, otherLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';

export const dynamic = 'force-static';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Privacy' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/privacy') };
}

const COLLECTED = ['phone', 'profile', 'session', 'contributions', 'saved', 'contact'] as const;
const NOT_STORED = ['nearMe', 'logs', 'cache', 'map'] as const;
const linkCls = 'font-medium text-secondary underline';

export default async function PrivacyPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Privacy');
  const strong = (c: React.ReactNode) => <strong>{c}</strong>;
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>
      <p className="mt-3 text-[15px]">{t('intro')}</p>

      <Section title={t('collectedTitle')}>
        <Card className="divide-y divide-line">
          {COLLECTED.map((k) => (
            <div key={k} className="px-4 py-3">
              <h3 className="font-semibold">{t(`collected.${k}.what`)}</h3>
              <p className="mt-0.5 text-sm">{t(`collected.${k}.why`)}</p>
            </div>
          ))}
        </Card>
        <p className="mt-2 text-sm text-muted">{t('browseFree')}</p>
      </Section>

      <Section title={t('notStoredTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          {NOT_STORED.map((k) => <p key={k}>{t.rich(`notStored.${k}`, { strong })}</p>)}
        </Card>
      </Section>

      <Section title={t('retentionTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t.rich('retention1', { strong })}</p>
          <p className="text-sm text-muted">{t('retention2')}</p>
        </Card>
      </Section>

      <Section title={t('deletionTitle')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t.rich('deletion1', { link: (c) => <Link href="/me" className={linkCls}>{c}</Link> })}</p>
          <p>{t.rich('deletion2', { link: (c) => <Link href="/contact" className={linkCls}>{c}</Link> })}</p>
        </Card>
      </Section>

      <Section title={t('legalTitle')}>
        <Card className="p-4 text-[15px]">
          <p>{t('legal')}</p>
        </Card>
      </Section>
    </div>
  );
}
