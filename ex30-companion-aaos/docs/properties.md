# Vehicle signals

Only supported, permitted, available values enter a snapshot. The app uses the public Android Automotive property manager in the signed-in car user’s process. The upstream project recorded the core driving and energy properties on a retail EX30. The display-unit preferences and usable capacity were also exercised on Google’s Android 15 Automotive image. [Android property reference](https://developer.android.com/reference/android/car/VehiclePropertyIds) · [Upstream EX30 property inventory](https://github.com/ifmeidan/ex-30-driver-display/blob/be10605dd7d427c99effbb98255ca3e31bac33aa/ex30-companion-aaos/docs/properties.md)

| Android property | How the display uses it |
| --- | --- |
| `PERF_VEHICLE_SPEED_DISPLAY` | Calibrated displayed speed in metres per second. The Pi converts to the selected unit, uses the magnitude in reverse and rounds to a whole number. |
| `VEHICLE_SPEED_DISPLAY_UNITS`, `DISTANCE_DISPLAY_UNITS` | Independent speed and distance preferences. If absent, US and GB Android locales default to mph and miles, other locales to km/h and kilometres. |
| `RANGE_REMAINING` | Car-estimated remaining distance in metres. A mile is 1,609.344 m. |
| `EV_BATTERY_LEVEL` | Remaining energy in Wh. Divide by `EV_CURRENT_BATTERY_CAPACITY` or, when unavailable, `INFO_EV_BATTERY_CAPACITY`. The factory’s displayed percentage can differ from this estimate. |
| `FUEL_LEVEL_LOW` | If the car reports low traction-battery energy, the small battery icon shows at least amber. The rounded percentage also selects amber at 15%, orange at 10%, and red at 5% and below. |
| `EV_BATTERY_AVERAGE_TEMPERATURE` | A snowflake beside the battery percentage appears below 0°C pack temperature. A reading at or above 0°C, or an unavailable reading, clears it. |
| `GEAR_SELECTION`, `PARKING_BRAKE_ON` | Highlight the selected gear and show the steady engaged parking brake independently. |
| `EV_BATTERY_INSTANTANEOUS_CHARGE_RATE` | Upstream observed the EX30 reports the opposite sign to Android’s specification. The app preserves its EX30 sign correction. The Pi gauge spans 200 kW draw and 100 kW regeneration. Those are drawing scales. Volvo’s exact available power, regen limits and friction braking require separate inputs. |
| `EV_CHARGE_PORT_CONNECTED`, `IGNITION_STATE` | Plug indicator and decisions about leaving or resuming the connection. |
| `EV_CHARGE_STATE` | Charging, full and error select the corresponding parked face. Full means the configured target was reached. Idle with a connected cable shows “Plugged in”. If the state is unavailable, Park, a connected cable and at least 100 W into the pack qualify as active charging. Motion, a driving gear or a disconnected cable rules out all four charging faces. |
| `EV_CHARGE_PERCENT_LIMIT`, `EV_CHARGE_TIME_REMAINING` | Optional target percentage and car-estimated seconds remaining. Android grants read access with the existing energy permission. Both were verified on Google’s Automotive emulator. Their availability on a retail EX30 remains unverified. |
| `NIGHT_MODE` | Cabin-light fallback when Android’s current UI mode is undefined. The service gives an explicit day/night UI configuration precedence. |

The low-energy flag, pack temperature and charging-state transitions were exercised with simulated readings on Google’s Android 15 Automotive image. Their availability to this app on a retail EX30 still needs confirmation.

There is no verified ordinary-app feed for the EX30’s recognized road-sign speed limit, the automatic rain-sensor indicator or the factory position-lamp status. The Pi leaves these off the display. The rendered parking-brake symbol reports engagement. A flashing fault indication would need its own source.

Display speed is requested at up to 10 Hz, power at 20 Hz, and other continuous properties at 1 Hz, within the rate bounds advertised by the vehicle. Other properties are read once or observed on change.
