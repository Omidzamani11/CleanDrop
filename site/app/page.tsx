import Image from "next/image";

const releaseBase =
  "https://github.com/Omidzamani11/CleanDrop/releases/latest/download";
const publicBasePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

const downloads = {
  installer: `${releaseBase}/CleanDrop-Setup-1.0.0.exe`,
  portable: `${releaseBase}/CleanDrop-1.0.0-win-x64.zip`,
  checksums: `${releaseBase}/SHA256SUMS.txt`,
};

const features = [
  {
    number: "01",
    title: "همه‌چیز روی دستگاه شما",
    copy: "فایل برای تحلیل یا پاک‌سازی به اینترنت، سرویس ابری یا مدل هوش مصنوعی فرستاده نمی‌شود.",
  },
  {
    number: "02",
    title: "OCR فارسی و انگلیسی",
    copy: "متن تصاویر و صفحه‌های اسکن‌شده با Tesseract محلی بررسی می‌شود تا ایمیل و شماره تلفن پیدا شوند.",
  },
  {
    number: "03",
    title: "بازسازی امن تصویر و PDF",
    copy: "تصاویر از روی پیکسل‌ها ساخته می‌شوند و PDF با Secure Flatten به سند تازه و بدون لایه‌های فعال تبدیل می‌شود.",
  },
  {
    number: "04",
    title: "تأیید قبل از اعلام موفقیت",
    copy: "CleanDrop خروجی را دوباره باز می‌کند، متادیتا و نواحی پوشانده‌شده را می‌سنجد و بعد گزارش می‌دهد.",
  },
];

const workflow = [
  ["۱", "بازرسی", "نوع واقعی فایل، هش، متادیتا، GPS و متن پنهان بررسی می‌شود."],
  ["۲", "مرور", "یافته‌ها را ببینید، انتخاب کنید و در صورت نیاز ناحیهٔ دستی بکشید."],
  ["۳", "پاک‌سازی", "یک فایل تازه ساخته می‌شود؛ فایل اصلی هرگز بازنویسی نمی‌شود."],
  ["۴", "تأیید", "خروجی با سیاست انتخاب‌شده بررسی و گزارش JSON خصوصی‌پسند تولید می‌شود."],
];

function DownloadArrow() {
  return <span aria-hidden="true">↓</span>;
}

export default function Home() {
  return (
    <div className="site-shell">
      <a className="skip-link" href="#main">
        رفتن به محتوای اصلی
      </a>

      <header className="site-header">
        <a className="brand" href="#top" aria-label="CleanDrop، ابتدای صفحه">
          <Image
            className="brand-mark"
            src={`${publicBasePath}/cleandrop-icon.png`}
            width={44}
            height={44}
            alt=""
            priority
          />
          <span>
            <strong>CleanDrop</strong>
            <small>پاک‌سازی خصوصی فایل</small>
          </span>
        </a>
        <nav aria-label="ناوبری اصلی">
          <a href="#how">روش کار</a>
          <a href="#security">امنیت</a>
          <a href="#download">دانلود</a>
          <a
            href="https://github.com/Omidzamani11/CleanDrop"
            target="_blank"
            rel="noreferrer"
          >
            کد منبع
          </a>
        </nav>
      </header>

      <main id="main">
        <section className="hero" id="top">
          <div className="hero-copy">
            <div className="eyebrow">
              <span className="status-dot" aria-hidden="true" />
              نسخهٔ ۱.۰ برای ویندوز — پردازش کاملاً محلی
            </div>
            <h1>
              قبل از ارسال،
              <br />
              <span>ردپای پنهان فایل</span> را پاک کنید.
            </h1>
            <p className="hero-lead">
              CleanDrop یک برنامهٔ متن‌باز برای یافتن و حذف متادیتا، GPS و
              اطلاعات حساس از تصویر و PDF است؛ با مرور دستی یافته‌ها و تأیید
              دوبارهٔ خروجی.
            </p>
            <div className="hero-actions">
              <a className="button button-primary" href={downloads.installer}>
                <DownloadArrow />
                دانلود نصب‌کنندهٔ ویندوز
              </a>
              <a className="button button-secondary" href="#preview">
                دیدن برنامه
              </a>
            </div>
            <div className="release-note">
              <span>Windows 10/11 · x64</span>
              <span>بدون نیاز به Python یا Tesseract</span>
              <span>AGPL-3.0-or-later</span>
            </div>
          </div>

          <div className="hero-proof" aria-label="خلاصهٔ امنیت CleanDrop">
            <div className="proof-head">
              <span>وضعیت پردازش</span>
              <strong>فقط روی این دستگاه</strong>
            </div>
            <div className="proof-flow" aria-hidden="true">
              <span>Inspect</span>
              <i>→</i>
              <span>Review</span>
              <i>→</i>
              <span>Sanitize</span>
              <i>→</i>
              <span>Verify</span>
            </div>
            <div className="proof-list">
              <div>
                <span>آپلود فایل</span>
                <strong className="safe">انجام نمی‌شود</strong>
              </div>
              <div>
                <span>بازنویسی فایل اصلی</span>
                <strong className="safe">انجام نمی‌شود</strong>
              </div>
              <div>
                <span>گزارش با دادهٔ خام حساس</span>
                <strong className="safe">ذخیره نمی‌شود</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="trust-strip" aria-label="قابلیت‌های اصلی">
          <span>JPG / JPEG / PNG</span>
          <span>PDF بدون رمز</span>
          <span>OCR: فارسی + English</span>
          <span>ExifTool + Tesseract همراه برنامه</span>
        </section>

        <section className="preview-section" id="preview">
          <div className="section-heading centered">
            <p>شفاف و قابل کنترل</p>
            <h2>قبل از پاک‌سازی، دقیقاً می‌بینید چه چیزی پیدا شده است.</h2>
            <span>
              یافته‌های خودکار را روشن یا خاموش کنید، ناحیهٔ دستی بکشید و نتیجه
              را در یک فایل تازه تحویل بگیرید.
            </span>
          </div>
          <div className="window-frame">
            <div className="window-bar" aria-hidden="true">
              <i />
              <i />
              <i />
              <span>CleanDrop 1.0</span>
            </div>
            <Image
              className="app-shot"
              src={`${publicBasePath}/cleandrop-desktop-fa.png`}
              width={1320}
              height={850}
              sizes="(max-width: 900px) 94vw, 1180px"
              alt="نمای واقعی رابط فارسی CleanDrop با فهرست فایل‌ها، یافته‌های حساس و پیش‌نمایش تصویر"
              priority
            />
          </div>
        </section>

        <section className="features-section" id="security">
          <div className="section-heading">
            <p>حریم خصوصی در معماری، نه در شعار</p>
            <h2>یک مسیر امن و قابل بررسی برای فایل‌های روزمره</h2>
          </div>
          <div className="feature-grid">
            {features.map((feature) => (
              <article className="feature-card" key={feature.number}>
                <span className="feature-number">{feature.number}</span>
                <h3>{feature.title}</h3>
                <p>{feature.copy}</p>
              </article>
            ))}
          </div>
        </section>

        <section className="workflow-section" id="how">
          <div className="workflow-copy">
            <div className="section-heading">
              <p>چهار قدم روشن</p>
              <h2>فایل را انتخاب کنید؛ کنترل تصمیم دست شما می‌ماند.</h2>
            </div>
            <p>
              CleanDrop هیچ نتیجه‌ای را صرفاً به‌خاطر ساخته‌شدن فایل موفق
              اعلام نمی‌کند. مرحلهٔ Verify باید تمام شود و بررسی‌های سیاست
              امنیتی پاس شوند.
            </p>
          </div>
          <ol className="workflow-list">
            {workflow.map(([number, title, copy]) => (
              <li key={number}>
                <span>{number}</span>
                <div>
                  <h3>{title}</h3>
                  <p>{copy}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="boundary">
          <div>
            <span className="boundary-label">مرز مسئولانه</span>
            <h2>CleanDrop یک ابزار کاهش ریسک است، نه تضمین صددرصدی.</h2>
          </div>
          <p>
            این نسخه اسکن بدافزار، تشخیص استگانوگرافی، تشخیص چهره یا حذف
            واترمارک انجام نمی‌دهد. فایل خروجی را پیش از انتشار بازبینی کنید و
            فایل اصلی را تا پایان کار نگه دارید.
          </p>
        </section>

        <section className="download-section" id="download">
          <div className="download-copy">
            <div className="eyebrow">
              <span className="status-dot" aria-hidden="true" />
              CleanDrop 1.0.0
            </div>
            <h2>آماده‌اید یک نسخهٔ پاک برای اشتراک‌گذاری بسازید؟</h2>
            <p>
              نصب‌کننده شامل موتورهای OCR و بررسی متادیتا است. اگر نصب
              نمی‌خواهید، نسخهٔ پرتابل را دریافت کنید.
            </p>
          </div>

          <div className="download-options">
            <article className="download-card recommended">
              <span className="card-kicker">پیشنهاد ما</span>
              <h3>نصب‌کنندهٔ ویندوز</h3>
              <p>نصب برای همان کاربر، میان‌بر Start و حذف آسان برنامه.</p>
              <a className="button button-primary" href={downloads.installer}>
                <DownloadArrow />
                دریافت فایل EXE
              </a>
              <small>حدود ۱۰۶ مگابایت</small>
            </article>
            <article className="download-card">
              <span className="card-kicker">بدون نصب</span>
              <h3>نسخهٔ پرتابل</h3>
              <p>فایل ZIP را باز کنید و CleanDrop.exe را اجرا کنید.</p>
              <a className="button button-secondary" href={downloads.portable}>
                <DownloadArrow />
                دریافت فایل ZIP
              </a>
              <small>حدود ۱۵۸ مگابایت</small>
            </article>
          </div>

          <div className="integrity">
            <div>
              <strong>بررسی اصالت دانلود</strong>
              <span>
                هش SHA-256 نصب‌کننده:
                <code>
                  9e1109ff296a887d875837ff6b35898fb265e297d29979febc21bc0e51ff15d6
                </code>
              </span>
            </div>
            <a href={downloads.checksums}>دانلود SHA256SUMS.txt</a>
          </div>

          <p className="unsigned-note">
            نسخهٔ نخست امضای دیجیتال تجاری ندارد؛ بنابراین ممکن است Windows
            SmartScreen هشدار نشان دهد. پیش از اجرا، هش بالا را با فایل
            SHA256SUMS مقایسه کنید.
          </p>
        </section>
      </main>

      <footer>
        <div className="brand footer-brand">
          <Image
            className="brand-mark"
            src={`${publicBasePath}/cleandrop-icon.png`}
            width={40}
            height={40}
            alt=""
          />
          <span>
            <strong>CleanDrop</strong>
            <small>Local-first privacy cleaner</small>
          </span>
        </div>
        <p>متن‌باز، بدون حساب کاربری، بدون آپلود فایل.</p>
        <div className="footer-links">
          <a href="https://github.com/Omidzamani11/CleanDrop">GitHub</a>
          <a href="https://github.com/Omidzamani11/CleanDrop/blob/main/SECURITY.md">
            امنیت
          </a>
          <a href="https://github.com/Omidzamani11/CleanDrop/blob/main/LICENSE">
            مجوز
          </a>
        </div>
      </footer>
    </div>
  );
}
