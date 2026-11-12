import './globals.css';

/** Last-resort 404 for URLs that never reach a locale (e.g. a malformed path); bilingual, no app chrome. */
export default function GlobalNotFound() {
  return (
    <html lang="bn">
      <body className="min-h-dvh">
        <main className="mx-auto max-w-xl px-4 py-16 text-center">
          <h1 className="text-2xl font-bold">পাতাটি পাওয়া যায়নি</h1>
          <p lang="en" className="mt-1 font-en text-muted">Page not found</p>
          <p className="mt-6 flex justify-center gap-4">
            <a href="/" className="rounded-chip bg-primary px-5 py-2.5 font-semibold text-on-primary">হোম</a>
            <a href="/en" lang="en" hrefLang="en" className="rounded-chip border border-line px-5 py-2.5 font-semibold">Home (English)</a>
          </p>
        </main>
      </body>
    </html>
  );
}
