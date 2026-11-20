# Setup

## Raspberry Pi

Start with 64-bit Raspberry Pi OS Lite, Bluetooth Classic on the Pi, a connected display and working internet for package installation. The installer uses the screen mode selected by Raspberry Pi OS. The layout is designed for a wide panel such as 1920 × 480 and scales uniformly to fit.

```sh
git clone https://github.com/bcapps/ex30-driver-display.git
cd ex30-driver-display
sudo sh display/install.sh
```

The installer creates the unprivileged `ex30-display` service user and starts a fullscreen Cage session at boot. The screen shows a name such as **EX30 Display A1B2**. A fresh display is discoverable for three minutes. Restart the display to open a new window if setup takes longer. For an existing installation, pull the new version and rerun the installer.

## Android Automotive

The fork’s package is `com.bcapps.ex30display`. It needs AAOS API 32 or later and Bluetooth Classic. Build with Android SDK Platform 35 and JDK 17 or 21.

```sh
cd ex30-companion-aaos
./gradlew :app:assembleDebug
```

The APK is `app/build/outputs/apk/debug/app-debug.apk`. Use ADB on an Automotive emulator or a development head unit that supports it.

```sh
adb install -r app/build/outputs/apk/debug/app-debug.apk
```

A retail EX30 needs an installation channel Volvo permits. This fork has no Google Play listing. The upstream Play app uses a different package and transport. A local debug APK by itself does not give a retail car an installation channel.

## First pairing

1. With the car parked, open **Calm Driver Display** and tap **Find display**.
2. Approve the permissions Android shows. Android can group vehicle speed under location, energy under car information and Bluetooth under nearby devices.
3. Select the exact name displayed on your Pi, then tap **Pair** in Android’s system dialog. There is no code to enter. The Pi saves the first bonded car that connects to its display service.

On later trips, the app connects to that display in the background. It closes the connection when the EX30 indicates the driver has left or its screen turns off. A connected charge port keeps the link active. If port status is unavailable, the app uses the car’s active charging state. After a head-unit reboot the service starts on the normal Android boot broadcast for the user. Force-stopping the Android app requires opening it again.

## Checking the display

```sh
systemctl status ex30-display
journalctl -b -u ex30-display
```

**Waiting for car** means the saved car is disconnected or its readings have stopped. **Restart display to pair** means the initial pairing window expired. A live dash in the speed position can also mean the car has withheld the speed property or its permission.

To pair a replacement car, forget the display in the old car’s Bluetooth settings. On the Pi, stop the kiosk, remove the old bond and clear the stored car address, then restart the kiosk.

```sh
sudo systemctl stop ex30-display
sudo bluetoothctl remove "$(sudo cat /var/lib/ex30-display/car)"
sudo rm /var/lib/ex30-display/car
sudo systemctl start ex30-display
```

## Preview and test

Run the preview and instrument tests from the repository root with Python 3 and Pycairo.

```sh
python3 display/preview.py day /tmp/ex30-day.png
python3 display/preview.py night /tmp/ex30-night.png
python3 display/preview.py night /tmp/ex30-welcome.png --welcome
python3 display/preview.py day /tmp/ex30-charging.png --charging
PYTHONPATH=display python3 -m unittest discover -s display/tests -v
```

The preview uses example readings. Supplying a saved lettering frame with `--lettering` uses the same Android-drawn glyphs as a live connection.
