package com.ex30companion

import android.car.VehiclePropertyIds
import android.car.VehicleUnit
import android.car.hardware.property.EvChargeState

/** Convert vehicle property values into portable display units and field names. */
object WireFieldMapper {

    data class Wire(val field: String, val value: Any)

    fun map(propertyId: Int, raw: Any?): Wire? {
        if (raw == null) return null
        return when (propertyId) {
            VehiclePropertyIds.VEHICLE_SPEED_DISPLAY_UNITS -> when ((raw as Number).toInt()) {
                VehicleUnit.MILES_PER_HOUR -> Wire("speed_unit", "mph")
                VehicleUnit.KILOMETERS_PER_HOUR -> Wire("speed_unit", "km/h")
                VehicleUnit.METER_PER_SEC -> Wire("speed_unit", "m/s")
                else -> null
            }
            VehiclePropertyIds.DISTANCE_DISPLAY_UNITS -> when ((raw as Number).toInt()) {
                VehicleUnit.MILE -> Wire("distance_unit", "mi")
                VehicleUnit.KILOMETER -> Wire("distance_unit", "km")
                VehicleUnit.METER -> Wire("distance_unit", "m")
                else -> null
            }
            VehiclePropertyIds.EV_CURRENT_BATTERY_CAPACITY ->
                Wire("usable_capacity_wh", (raw as Number).toFloat())
            VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY ->
                Wire("speed_display_aaos", (raw as Number).toFloat())
            VehiclePropertyIds.EV_BATTERY_LEVEL ->
                Wire("soc_aaos", (raw as Number).toFloat())
            // EV_BATTERY_INSTANTANEOUS_CHARGE_RATE per VHAL spec is mW with
            // positive = charging (regen / plugged in), negative = discharging.
            // The real EX30 ships the opposite sign (verified during the
            // 2026-05-14 charge cycle on the retail car): negative = charging
            // and regen, positive = discharging. We invert here so the wire
            // field matches the spec the Pi gauges code against — keeps the
            // receiver consistent for this EX30 implementation.
            VehiclePropertyIds.EV_BATTERY_INSTANTANEOUS_CHARGE_RATE ->
                Wire("battery_power_mw", -(raw as Number).toFloat())
            VehiclePropertyIds.RANGE_REMAINING ->
                Wire("range_m_aaos", (raw as Number).toFloat())
            VehiclePropertyIds.GEAR_SELECTION ->
                Wire("gear_selected", gearName((raw as Number).toInt()))
            VehiclePropertyIds.PARKING_BRAKE_ON ->
                Wire("parking_brake", raw as Boolean)
            VehiclePropertyIds.EV_CHARGE_PORT_CONNECTED ->
                Wire("charge_port_connected", raw as Boolean)
            VehiclePropertyIds.EV_CHARGE_STATE -> when (raw) {
                EvChargeState.STATE_CHARGING -> Wire("charging_active", true)
                EvChargeState.STATE_NOT_CHARGING, EvChargeState.STATE_FULLY_CHARGED,
                EvChargeState.STATE_ERROR -> Wire("charging_active", false)
                else -> null
            }
            VehiclePropertyIds.EV_CHARGE_PERCENT_LIMIT -> Wire("charge_target_pct", (raw as Number).toFloat())
            VehiclePropertyIds.EV_CHARGE_TIME_REMAINING -> Wire("charge_seconds_remaining", (raw as Number).toInt())
            VehiclePropertyIds.NIGHT_MODE ->
                Wire("night_mode", raw as Boolean)
            VehiclePropertyIds.INFO_EV_BATTERY_CAPACITY ->
                Wire("pack_capacity_wh", (raw as Number).toFloat())
            else -> null
        }
    }

    // android.car.VehicleGear bit values — pinned here rather than referenced
    // because the constants moved between API 30 and 33; the underlying bits
    // are stable across all versions the EX30 has shipped.
    private fun gearName(bits: Int): String = when (bits) {
        0x0001 -> "N"  // GEAR_NEUTRAL
        0x0002 -> "R"  // GEAR_REVERSE
        0x0004 -> "P"  // GEAR_PARK
        0x0008 -> "D"  // GEAR_DRIVE (and any GEAR_1..GEAR_9 collapse to D for our purposes)
        in 0x0010..0x1000 -> "D"
        else -> "UNKNOWN"
    }
}
