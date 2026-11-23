# App permissions

| Android permission | Purpose |
| --- | --- |
| `BLUETOOTH_SCAN`, `BLUETOOTH_CONNECT` | Find the named Pi during parked setup, pair through Android and connect to its bonded RFCOMM service. The scan is declared `neverForLocation`. |
| `CAR_SPEED`, `CAR_ENERGY` | Runtime permissions for displayed speed, energy, range, pack power and battery temperature. Android controls their prompt wording. |
| `READ_CAR_DISPLAY_UNITS`, `CAR_POWERTRAIN`, `CAR_EXTERIOR_ENVIRONMENT`, `CAR_ENERGY_PORTS`, `CAR_INFO` | Display preferences, selected gear, parking brake, ignition, night fallback, charge-port state and nominal battery capacity. |
| `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_CONNECTED_DEVICE`, `RECEIVE_BOOT_COMPLETED` | Keep the selected display connected in the background and resume after boot. |

The manifest contains the namespaced car permissions. Android decides which properties are available to this app on each vehicle. [Manifest](../app/src/main/AndroidManifest.xml)
