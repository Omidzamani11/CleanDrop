import type { Metadata } from "next";
import { headers } from "next/headers";
import "./globals.css";

function siteUrl(requestHeaders: Headers) {
  const host =
    requestHeaders.get("x-forwarded-host") ??
    requestHeaders.get("host") ??
    "127.0.0.1:3000";
  const protocol =
    requestHeaders.get("x-forwarded-proto") ??
    (host.startsWith("127.") || host.startsWith("localhost")
      ? "http"
      : "https");
  return new URL(`${protocol}://${host}`);
}

export async function generateMetadata(): Promise<Metadata> {
  const base = siteUrl(await headers());
  const socialImage = new URL("/og.png", base).toString();

  return {
    metadataBase: base,
    title: "CleanDrop — پاک‌سازی خصوصی تصویر و PDF",
    description:
      "CleanDrop متادیتا، GPS و اطلاعات حساس را روی دستگاه شما از تصویر و PDF پیدا و پاک می‌کند؛ بدون آپلود فایل.",
    applicationName: "CleanDrop",
    alternates: { canonical: "/" },
    icons: {
      icon: "/cleandrop-icon.png",
      shortcut: "/cleandrop-icon.png",
      apple: "/cleandrop-icon.png",
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
}

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
