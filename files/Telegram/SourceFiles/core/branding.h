/*
This file is part of Telegram Desktop,
the official desktop application for the Telegram messaging service.

For license and copyright information please follow this link:
https://github.com/telegramdesktop/tdesktop/blob/master/LEGAL
*/
#pragma once

#include "base/const_string.h"

namespace Branding {

// ShapitoGram: витрина приложения. AppName — то, что видит пользователь в
// заголовке окна, на экране About и в ярлыке; ApplicationName — технический
// идентификатор (папка с данными, ключи реестра, имя exe), поэтому без
// пробелов. Меняем оба, чтобы «Telegram» не остался нигде.
constexpr auto AppName = "ShapitoGram Desktop"_cs;
constexpr auto ShortAppName = "ShapitoGram"_cs;
constexpr auto ApplicationName = "ShapitoGramDesktop"_cs;
constexpr auto CompanyName = "ShapitoGram"_cs;

#ifdef _DEBUG
constexpr auto WindowsIconPath = "Resources/OwpenGram/art/icon256_debug.ico"_cs;
#else
constexpr auto WindowsIconPath = "Resources/OwpenGram/art/icon256.ico"_cs;
#endif
constexpr auto MacOSIconName = "Icon.icns"_cs;
constexpr auto LinuxIconBase = "Resources/OwpenGram/art/icon"_cs;

#ifdef _DEBUG
constexpr auto LogoPath = ":/gui/art/logo_256_debug.png"_cs;
constexpr auto LogoNoMarginPath = ":/gui/art/logo_256_debug.png"_cs;
#else
constexpr auto LogoPath = ":/gui/art/logo_256.png"_cs;
constexpr auto LogoNoMarginPath = ":/gui/art/logo_256_no_margin.png"_cs;
#endif
constexpr auto PlaneWhitePath = ":/gui/plane_white.svg"_cs;
constexpr auto BusinessLogoPath = ":/gui/art/business_logo.png"_cs;
constexpr auto AffiliateLogoPath = ":/gui/art/affiliate_logo.png"_cs;

constexpr auto TrayMonochromePath = ":/gui/icons/tray/monochrome.svg"_cs;
constexpr auto TrayMonochromeAttentionPath = ":/gui/icons/tray/monochrome_attention.svg"_cs;
constexpr auto TrayMonochromeMutePath = ":/gui/icons/tray/monochrome_mute.svg"_cs;

constexpr auto BundleIdentifier = "org.shapitogram.desktop"_cs;

#ifdef _DEBUG
constexpr auto LinuxAppId = "org.shapitogram.desktop.Debug"_cs;
#else
constexpr auto LinuxAppId = "org.shapitogram.desktop"_cs;
#endif

// ShapitoGram: платежи за реальные деньги в этом билде отключены полностью.
// Точки применения: Session::premiumCanBuy() / Session::appConfigRefreshed()
// (main_session.cpp), Form::requestForm() (payments_form.cpp) и
// CheckoutProcess::Start() (payments_checkout_process.cpp).
constexpr auto PaymentsDisabled = true;

// ShapitoGram: подарки оплачиваются звёздами (Stars), а не реальными деньгами,
// поэтому раздел подарков остаётся доступен при PaymentsDisabled = true.
// Управляет только видимостью входа в «Отправить подарок» в настройках.
constexpr auto StarsGiftsEnabled = true;

} // namespace Branding
