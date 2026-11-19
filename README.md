# EX30 Driver Display

A Bluetooth instrument display for the Volvo EX30. A read-only Android Automotive app sends readings directly to a Raspberry Pi. The instruments follow the layout of the **EX90 Calm** display, with the EX30's light and dark styling.

![Day preview with a centered speed of zero, range and battery charge to the right, and Park selected](docs/calm-day.png)
![Night preview of the same instruments](docs/calm-night.png)

The screenshots come from the running Pi kiosk on a 1920 × 480 virtual screen. Speed uses **Volvo Novum Regular with tabular lining digits** when available. The EX30 emulator ships Novum Regular 2.001 at `/product/fonts/VolvoNovum-Regular.ttf`. The launcher and System UI contain identical copies. Its tabular 8 and 0 are 530 and 510 font units wide and both are 712 units tall. At the 139-pixel height in Volvo’s published EX30 Calm view, those outlines predict widths of 103.5 and 99.6 pixels. The image measures 104 and 100. The 12-pixel gap comes from the image. The factory screen’s exact text-style declaration on retail 2.x remains unverified. [Volvo’s EX30 Calm view](https://www.volvocars.com/uk/cars/ex30-electric/features/) · [Volvo’s archived EX30 emulator catalog](https://web.archive.org/web/20260903221015id_/https://developer.volvocars.com/sdk/volvo-sys-img.xml)

Speed is centred and occupies about 34% of the wide panel’s height, following the EX90 photograph. Its digit width and spacing follow the EX30 top strip. The other readings use Regular, and the gear column uses SemiLight and Medium. On systems without the Volvo font, including the Google Automotive emulator used for these screenshots, speed uses the project’s Inter font at weight 360. [Volvo’s EX90 photograph, p. 43](https://www.volvocars-news.ch/wp-content/uploads/2022/12/Volvo_FTM_2_2022_DE.pdf#page=43)

## Connect

1. Install the Pi display on a Raspberry Pi with Bluetooth Classic and an attached screen.
2. Open **Calm Driver Display** on the parked car and tap **Find display**. Grant the vehicle and Nearby devices permissions Android requests.
3. Select the **EX30 Display** name shown on the Pi and approve Android’s pairing dialog. The Pi needs only its screen. Subsequent trips reuse the saved bond.

No Wi-Fi password, camera, OBD adapter or internet connection is needed for the drive. This fork has its own Android application ID. See the installation and build steps, including retail installation availability. [Setup guide](SETUP.md)

## What appears on screen

| Instrument | Source and behavior |
| --- | --- |
| Speed | Calibrated display speed from the EX30. The unit follows the car’s exposed preference. |
| Range | The car’s remaining-range estimate in miles or kilometres. Distance and speed units are independent. |
| Battery | Percentage calculated from remaining energy and usable capacity, with nominal capacity as a fallback. Volvo can round or reserve energy differently. |
| Gear and parking brake | The selected P, R, N or D is highlighted. The red parking-brake symbol follows its own switch. |
| Power and charging | A signed battery-power bar estimates draw and regeneration. A plug appears when the cable is connected. The factory meter’s available-power limits and friction-brake section require more signals. |
| Day and night | The app sends AAOS’s current appearance, including changes while the setup screen is closed. The cabin night flag is a fallback. |

A missing speed displays a dash. Each snapshot replaces all the previous readings. If the car goes silent for three seconds, the Pi clears the instruments. The photograph’s recognized speed-limit sign, automatic-wiper indicator and position lamps are left empty because this app has no verified read for their factory states. Use the car’s instruments for warnings. [Vehicle signals](ex30-companion-aaos/docs/properties.md)

## Verification

Tested with Google’s Android 15 Automotive emulator and a separate ARM64 Linux VM running BlueZ and the Pi receiver. The two systems paired over virtual Bluetooth radios with Wi-Fi disabled. The display followed background day/night changes, recovered after an Android reboot and a receiver restart, and cleared a frozen speed reading in about three seconds before reconnecting. The renderer tests cover wide and 16:9 screens and lettering from both versions of the car app. Physical EX30 Bluetooth policy, a Raspberry Pi’s radio and the attached panel still need a hardware test. [Live kiosk frame with 60 mph, 100 mi of range and 90% charge](docs/live-mph.png)

## Project

The car app lives in `ex30-companion-aaos/`. The Pi kiosk, renderer and installer live in `display/`. The original `ex30-companion-runner/` remains in the shared history and source tree for upstream merges. This fork’s installer launches the Bluetooth kiosk. [Original project by ifmeidan](https://github.com/ifmeidan/ex-30-driver-display)

The EX30 day and night screen images supplied the main foreground and background colours. The colours on any individual panel depend on its calibration. [Volvo EX90 Calm manual](https://www.volvocars.com/static/support-content/pdfs/uk_en-GB_ex90_2025_UM_56de2ae2718076a243a7173854585416.pdf) · [EX30 day reference](https://www.volvocars.com/uk/cars/ex30-electric/features/) · [EX30 night reference](https://www.vosautobedrijven.nl/modellen/volvo-ex30/)
