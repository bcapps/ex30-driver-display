# Calm display Bluetooth stream

The Pi advertises a bonded RFCOMM service with UUID `9e457bc1-0291-4dcb-8427-919da22db81f`. Android discovers the RFCOMM channel via SDP. There is one car-to-Pi stream, UTF-8 JSON with one object per newline. [Android RFCOMM sockets](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#createRfcommSocketToServiceRecord(java.util.UUID)) · [BlueZ profile API](https://bluez.readthedocs.io/en/latest/profile-api/)

The first frame has type `lettering`, version 1. It contains the ordered instrument labels, per-face advances in pixels, and a transparent base64 PNG. Its six-column grid has 320 × 192 px cells, in two blocks of four rows. Block 0 supplies the range, charge and inactive gear letters. Block 1 supplies the speed digits and selected gear. The optional `speedRow` is 1 in new frames and defaults to 0 for older senders.

Digits use a 216 px em and a 174 px baseline. Other labels use 128 and 150 px respectively. Each label starts 4 px from the left edge. New senders draw range and charge in Novum SemiLight, select tabular digits and request the cap-height percent sign. The Pi measures the visible zero and percent sign once per connection so older senders also display the smaller, bottom-aligned sign. The Pi tints the lettering for each palette. Font files stay on the car.

Each subsequent frame has type `state` and a complete `fields` object. This sample describes 60 mph and 100 miles of range.

```json
{"type":"state","fields":{"speed_display_aaos":26.8224,"speed_unit":"mph","range_m_aaos":160934.4,"distance_unit":"mi","night_mode":false}}
```

Missing fields clear the previous value. Numeric fields carry m/s, metres, Wh or mW as described in the property table. The selected gear is a letter. Switches are booleans. A positive normalized power value means charging or regeneration. [Field sources](../docs/properties.md) · [Android wire mapping](../app/src/main/java/com/ex30companion/WireFieldMapper.kt)

Charging-capable senders also supply `charging_active` when the car reports a known charge state, `charge_target_pct` for the selected limit, and `charge_seconds_remaining` for its estimate. Each is optional. The lettering frame can include `chargingAdvances` for `Charging`, `Done in`, `h`, `min`, `kW`, and the decimal point in that order. They occupy 320 × 96 px tiles in the last two columns of the bottom row of each block, left to right then top to bottom, at a 72 px em and a 74 px baseline. Earlier receivers ignore these cells. New receivers use local text for charging words missing from older senders.

The optional boolean `before_drive` means the sender has yet to observe a driving gear or motion since waking. The Pi also requires Park and zero speed for the welcome face. An absent flag selects the existing driving or charging face. Optional `welcomeAdvances` contains the widths of “Hello” and “Press the brake and select D or R to start”. Both use the last 640 × 96 px strip of the existing atlas, starting at x = 1284. Their baselines are y = 1507 and 1534 at 88 and 32 px respectively.

Android sends changed readings up to 20 times a second and a current snapshot at least once per second while connected. The Pi allows 15 seconds for initial lettering and state, then clears its instruments after three seconds without a valid snapshot. Each reconnect starts with fresh lettering and a full state.
