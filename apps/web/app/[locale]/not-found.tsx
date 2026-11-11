import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';

export default function NotFound() {
  const t = useTranslations('NotFound');
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold">{t('title')}</h1>
      <p className="mt-2 text-muted">{t('body')}</p>
      <Link href="/explore" className="mt-6 inline-block rounded-chip bg-primary px-5 py-2.5 font-semibold text-on-primary">
        {t('explore')}
      </Link>
    </div>
  );
}
