import type { Metadata } from "next";
import { Geist, Geist_Mono, Sora, Heebo } from "next/font/google";
import "./globals.css";
import { CartProvider } from "@/context/CartContext";
import { CartDrawer } from "@/components/cart/CartDrawer";
import { ToastProvider } from "@/context/ToastContext";
import { ConfirmProvider } from "@/context/ConfirmContext";
import { StorefrontThemeProvider } from "@/context/StorefrontThemeContext";
import { UiLocaleProvider } from "@/context/UiLocaleContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const headingFont = Sora({
  variable: "--font-heading-sora",
  weight: ["600", "700", "800"],
  subsets: ["latin"],
});

const heebo = Heebo({
  variable: "--font-heebo",
  subsets: ["latin", "hebrew"],
  weight: ["400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: {
    template: "%s | MultiVendor",
    default: "MultiVendor Storefront",
  },
  description: "Next-generation multi-tenant e-commerce platform.",
  openGraph: {
    title: "MultiVendor Storefront",
    description: "Next-generation multi-tenant e-commerce platform.",
    type: "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="he"
      dir="rtl"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} ${headingFont.variable} ${heebo.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <UiLocaleProvider>
          <ToastProvider>
            <ConfirmProvider>
              <CartProvider>
                <StorefrontThemeProvider>
                  {children}
                  <CartDrawer />
                </StorefrontThemeProvider>
              </CartProvider>
            </ConfirmProvider>
          </ToastProvider>
        </UiLocaleProvider>
      </body>
    </html>
  );
}
