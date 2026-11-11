import type { Metadata } from 'next';
import { getTranslations, setRequestLocale } from 'next-intl/server';
import { FilePlus2, MessageSquareWarning, PencilLine, ShieldCheck } from 'lucide-react';
import { asLocale } from '@/lib/locale';
import { localeAlternates } from '@/lib/meta';
import { Link } from '@/i18n/navigation';
import { Card, Section } from '@/components/ui';

type Props = { params: Promise<{ locale: string }> };

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const locale = asLocale((await params).locale);
  const t = await getTranslations({ locale, namespace: 'Contribute' });
  return { title: t('metaTitle'), alternates: localeAlternates(locale, '/contribute') };
}

const ACTIONS = [
  { type: 'new_place', Icon: FilePlus2 },
  { type: 'correction', Icon: PencilLine },
  { type: 'report', Icon: MessageSquareWarning },
] as const;

export default async function ContributePage({ params }: Props) {
  const locale = asLocale((await params).locale);
  setRequestLocale(locale);
  const t = await getTranslations('Contribute');
  return (
    <div className="pt-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p className="mt-1 text-sm text-muted">{t('intro')}</p>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {ACTIONS.map(({ type, Icon }) => (
          <Link key={type} href={`/contribute/new?type=${type}`} className="rounded-card border border-line bg-surface p-4 shadow-card hover:border-secondary">
            <Icon className="h-7 w-7 text-secondary" aria-hidden />
            <span className="mt-2 block font-semibold">{t(`actions.${type}.title`)}</span>
            <span className="block text-sm text-muted">{t(`actions.${type}.body`)}</span>
          </Link>
        ))}
      </div>
      <Section title={t('howTitle')}>
        <Card className="p-4 text-sm">
          <ol className="list-decimal space-y-1 pl-5">
            <li>{t('step1')}</li>
            <li>{t('step2')}</li>
            <li>{t('step3')}</li>
            <li>{t('step4')}</li>
          </ol>
          <p className="mt-3 flex items-start gap-2 text-muted"><ShieldCheck className="h-4 w-4 shrink-0 text-secondary" aria-hidden />
            <span>{t.rich('privacy', { link: (c) => <Link href="/guidelines" className="underline">{c}</Link> })}</span></p>
        </Card>
      </Section>
    </div>
  );
}
