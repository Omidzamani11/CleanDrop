import type { Metadata } from "next";
import "./globals.css";

const publicSiteUrl =
  process.env.NEXT_PUBLIC_SITE_URL ??
  (process.env.VERCEL_PROJECT_PRODUCTION_URL
    ? `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`
    : "https://omidzamani11.github.io/CleanDrop");
const publicSite = new URL(
  publicSiteUrl.endsWith("/") ? publicSiteUrl : `${publicSiteUrl}/`,
);
const publicBasePath =
  process.env.NEXT_PUBLIC_BASE_PATH ??
  publicSite.pathname.replace(/\/$/, "");
const metadataBase = new URL(
  publicSiteUrl.endsWith("/") ? publicSiteUrl : `${publicSiteUrl}/`,
);
const socialImage = new URL(
  `${publicBasePath}/og.png`,
  publicSite.origin,
).toString();

export const metadata: Metadata = {
  metadataBase,
  title: "CleanDrop — پاک‌سازی خصوصی تصویر و PDF",
  description:
    "CleanDrop متادیتا، GPS و اطلاعات حساس را روی دستگاه شما از تصویر و PDF پیدا و پاک می‌کند؛ بدون آپلود فایل.",
  applicationName: "CleanDrop",
  alternates: { canonical: publicSiteUrl },
  icons: {
    icon: `${publicBasePath}/cleandrop-icon.png`,
    shortcut: `${publicBasePath}/cleandrop-icon.png`,
    apple: `${publicBasePath}/cleandrop-icon.png`,
  },
  openGraph: {
    type: "website",
    locale: "fa_IR",
    title: "CleanDrop — قبل از ارسال، ردپای پنهان فایل را پاک کنید",
    description:
      "پاک‌سازی محلی متادیتا و اطلاعات حساس از تصویر و PDF، همراه با مرور دستی و تأیید خروجی.",
    siteName: "CleanDrop",
    images: [
      {
        url: socialImage,
        width: 1733,
        height: 907,
        alt: "CleanDrop، پاک‌سازی خصوصی فایل بدون آپلود",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: "CleanDrop — پاک‌سازی خصوصی فایل",
    description:
      "تصویر و PDF را بدون آپلود، روی دستگاه خود بررسی و پاک‌سازی کنید.",
    images: [socialImage],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
