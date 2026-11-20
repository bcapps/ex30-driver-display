# EX30 Driver Display for Android Automotive

The parked setup screen pairs with a Pi by name. A connected-device foreground service reads the EX30’s vehicle properties, observes Android’s light/dark configuration and sends complete snapshots to the selected display through a bonded Bluetooth Classic socket. The car also paints the instrument lettering. [Setup and build instructions](../SETUP.md) · [Vehicle properties](docs/properties.md) · [Bluetooth protocol](pi_bridge/protocol.md)

The application ID is `com.bcapps.ex30display`. The package name for source classes remains `com.ex30companion` to keep the shared history easy to merge. Every Android build runs the upstream vehicle-property write API check.
