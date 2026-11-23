# Calm display Bluetooth stream

The Pi advertises a bonded RFCOMM service with UUID `9e457bc1-0291-4dcb-8427-919da22db81f`. Android discovers the RFCOMM channel via SDP. There is one car-to-Pi stream, UTF-8 JSON with one object per newline. [Android RFCOMM sockets](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#createRfcommSocketToServiceRecord(java.util.UUID)) · [BlueZ profile API](https://bluez.readthedocs.io/en/latest/profile-api/)

The first frame has type `lettering` and version `2`. Both endpoints use this single format. Android sends one transparent 1920 × 1632 image in `png` (base64) and the 50 corresponding advance widths in `advances` (pixels). The Pi validates the complete frame before displaying vehicle data.

The first six rows use 320 × 192 px cells, six across. In order, they contain the reading digits 0–9, P/R/N/D, `km/h`, `mph`, `m/s`, `mi`, `km`, `m`, `%`, the dash `–`, the speed digits 0–9 and the selected P/R/N/D. Digits use a 216 px em and a 174 px baseline. Other instruments use 128 and 150 px respectively. The Pi measures the visible zero and percent glyphs to size and align the numbers for the font on the car.

Five rows of 640 × 96 px caption cells follow, three across, each with a 72 px baseline. All cells have a 4 px left inset. The Pi tints the same lettering for light and dark mode. Font files stay on the car. Both endpoints define the caption order and font sizes. [Android painter](../app/src/main/java/com/ex30companion/DisplayLettering.kt) · [Pi renderer](../../display/cluster.py)

Each subsequent frame has type `state` and a complete `fields` object. This sample describes 60 mph and 100 miles of range.

```json
{"type":"state","fields":{"speed_display_aaos":26.8224,"speed_unit":"mph","range_m_aaos":160934.4,"distance_unit":"mi","night_mode":false}}
```

Missing fields clear the previous value. Numeric fields carry m/s, metres, Wh or mW as described in the property table. The selected gear is a letter. Switches are booleans. A positive normalized power value means charging or regeneration. [Field sources](../docs/properties.md) · [Android wire mapping](../app/src/main/java/com/ex30companion/WireFieldMapper.kt)

`charge_state` carries `idle`, `charging`, `full` or `fault` when the car reports a known state. `charge_port_connected` reports the cable independently, `charge_target_pct` is the selected limit, and `charge_seconds_remaining` is the estimated time remaining. Each field is optional.

`outside_temp_c` and `pack_temp_c` carry independent readings in degrees Celsius. `temperature_unit` is `C` or `F` and applies to the displayed outside reading. `battery_low` carries the vehicle’s low-energy flag. An unavailable reading is omitted from the snapshot.

Android sets `before_drive` to true until it observes a driving gear or motion after waking. The Pi also requires Park and zero speed for the welcome face.

Android sends changed readings up to 20 times a second and a current snapshot at least once per second while connected. The Pi allows 15 seconds for initial lettering and state, then clears its instruments after three seconds without a valid snapshot. Each reconnect starts with fresh lettering and a full state.
