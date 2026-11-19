# EX30 Driver Display

A Bluetooth instrument display for the Volvo EX30. A read-only Android Automotive app sends readings directly to a Raspberry Pi. The instruments follow the layout of the **EX90 Calm** display, with the EX30's light and dark styling.

![Day preview with a centered speed of zero, range and battery charge to the right, and Park selected](docs/calm-day.png)
![Night preview of the same instruments](docs/calm-night.png)

The previews use the EX90 reference photograph’s example readings and lettering rendered by Google’s Automotive emulator. On the car, the app asks Android for its installed **Volvo Novum** and sends the rendered digits and short labels once per connection. Android supplies a system typeface if those families are unavailable. Volvo’s EX30 image names all three weights used here. Of its five installed weights, Regular came closest to the large 8 and 0 in the EX30 day reference. The gear column uses SemiLight and Medium. The exact appearance on a retail 2.x head unit still needs an on-car check.

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

Tested with Google’s Android 15 Automotive emulator and a separate ARM64 Linux VM running BlueZ, the Pi receiver and Cage. The two systems paired over virtual Bluetooth radios with Wi-Fi disabled. The display followed background day/night changes, recovered after an Android reboot and a receiver restart, and cleared a frozen speed reading in about three seconds before reconnecting. Six renderer and stream regression tests pass. Physical EX30 Bluetooth policy, a Raspberry Pi’s radio and the attached panel still need a hardware test. [Live kiosk frame with 60 mph, 100 mi of range and 90% charge](docs/live-mph.png)

## Project

The car app lives in `ex30-companion-aaos/`. The Pi kiosk, renderer and installer live in `display/`. The original `ex30-companion-runner/` remains in the shared history and source tree for upstream merges. This fork’s installer launches the Bluetooth kiosk. [Original project by ifmeidan](https://github.com/ifmeidan/ex-30-driver-display)

Placement follows an EX90 Calm driver-display photograph. The EX30 day and night screen images supplied the main foreground and background colours. The colours on any individual panel depend on its calibration. [Volvo EX90 Calm manual](https://www.volvocars.com/static/support-content/pdfs/uk_en-GB_ex90_2025_UM_56de2ae2718076a243a7173854585416.pdf) · [EX30 day reference](https://volvocarsbrisbanenorth.com.au/cars/volvo-ex30/features/) · [EX30 night reference](https://www.vosautobedrijven.nl/modellen/volvo-ex30/)
