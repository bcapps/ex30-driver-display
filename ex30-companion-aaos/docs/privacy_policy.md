# Data handling

EX30 Driver Display uses Bluetooth for a local connection to the selected display. The app reads the vehicle signals listed in the property catalog and sends current readings and rendered instrument lettering to the paired Pi. Neither endpoint records a trip history. [Vehicle signals](properties.md)

The Android app stores the selected Pi’s Bluetooth address in its private preferences. The Pi stores the selected car’s Bluetooth address in its service state directory. Android and BlueZ retain their own pairing keys. The project includes instructions for clearing a pairing. [Setup](../../SETUP.md)
