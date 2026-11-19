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
  const t = await getTranslations({ locale, namespace: 'Terms' });
  return { title: t('title'), description: t('description'), alternates: localeAlternates(locale, '/terms') };
}

const linkCls = 'font-medium text-secondary underline';

export default async function TermsPage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Terms');
  const strong = (c: React.ReactNode) => <strong>{c}</strong>;
  const link = (href: string) => (c: React.ReactNode) => <Link href={href} className={linkCls}>{c}</Link>;
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p lang={otherLocale(locale)} className={`text-sm text-muted ${locale === 'bn' ? 'font-en' : ''}`}>{t('subtitleOther')}</p>
      <p className="mt-3 text-[15px]">{t('intro')}</p>

      <Section title={t('s1Title')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t.rich('s1p1', { link: link('/data-policy') })}</p>
          <p>{t.rich('s1p2', { strong })}</p>
          <p>{t('s1p3')}</p>
        </Card>
      </Section>

      <Section title={t('s2Title')}>
        <Card className="p-4 text-[15px]">
          <p>{t('s2p1')}</p>
        </Card>
      </Section>

      <Section title={t('s3Title')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t('s3intro')}</p>
          <ul className="list-disc space-y-1 pl-5">
            <li>{t('s3li1')}</li>
            <li>{t('s3li2')}</li>
            <li>{t('s3li3')}</li>
          </ul>
          <p>{t.rich('s3p2', { link: link('/guidelines') })}</p>
        </Card>
      </Section>

      <Section title={t('s4Title')}>
        <Card className="p-4 text-[15px]">
          <p>{t('s4p1')}</p>
        </Card>
      </Section>

      <Section title={t('s5Title')}>
        <Card className="p-4 text-[15px]">
          <ul className="list-disc space-y-1 pl-5">
            <li>{t('s5li1')}</li>
            <li>{t('s5li2')}</li>
            <li>{t('s5li3')}</li>
          </ul>
        </Card>
      </Section>

      <Section title={t('s6Title')}>
        <Card className="space-y-2 p-4 text-[15px]">
          <p>{t('s6p1')}</p>
          <p>{t.rich('s6p2', { privacy: link('/privacy'), contact: link('/contact') })}</p>
        </Card>
      </Section>
    </div>
  );
}
