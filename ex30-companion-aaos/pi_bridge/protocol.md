# Calm display Bluetooth stream

The Pi advertises a bonded RFCOMM service with UUID `9e457bc1-0291-4dcb-8427-919da22db81f`. Android discovers the RFCOMM channel via SDP. There is one car-to-Pi stream, UTF-8 JSON with one object per newline. [Android RFCOMM sockets](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#createRfcommSocketToServiceRecord(java.util.UUID)) · [BlueZ profile API](https://bluez.readthedocs.io/en/latest/profile-api/)

The first frame has type `lettering`, version 1. It contains the ordered instrument labels, per-face advances in pixels, and a transparent base64 PNG. Its six-column grid has 320 × 192 px cells, in two blocks of four rows. Block 0 holds Regular readings and SemiLight inactive gear letters. Block 1 holds the SemiLight speed digits and Medium gear letters. The optional `speedRow` selects the block for speed digits. It is 1 in new frames and defaults to 0 for older senders. The Pi measures the selected zero’s visible ink once per connection to size the speed. Digits use a 216 px em and a 174 px baseline. Other labels use 128 and 150 px respectively. Each glyph starts 4 px from the left edge. The Pi colours this transient image for each palette. Font files stay on the car.

Each subsequent frame has type `state` and a complete `fields` object. This sample describes 60 mph and 100 miles of range.

```json
{"type":"state","fields":{"speed_display_aaos":26.8224,"speed_unit":"mph","range_m_aaos":160934.4,"distance_unit":"mi","night_mode":false}}
```

Missing fields clear the previous value. Numeric fields carry m/s, metres, Wh or mW as described in the property table. The selected gear is a letter. Switches are booleans. A positive normalized power value means charging or regeneration. [Field sources](../docs/properties.md) · [Android wire mapping](../app/src/main/java/com/ex30companion/WireFieldMapper.kt)

Android sends changed readings up to 20 times a second and a current snapshot at least once per second while connected. The Pi allows 15 seconds for initial lettering and state, then clears its instruments after three seconds without a valid snapshot. Each reconnect starts with fresh lettering and a full state.
