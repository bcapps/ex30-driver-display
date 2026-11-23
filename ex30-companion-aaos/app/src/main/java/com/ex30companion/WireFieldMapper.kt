package com.ex30companion

import android.car.VehicleGear
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
            VehiclePropertyIds.EV_BATTERY_AVERAGE_TEMPERATURE -> Wire("pack_temp_c", raw as Float)
            VehiclePropertyIds.FUEL_LEVEL_LOW -> Wire("battery_low", raw as Boolean)
            VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY ->
                Wire("speed_display_aaos", (raw as Number).toFloat())
            VehiclePropertyIds.EV_BATTERY_LEVEL ->
                Wire("soc_aaos", (raw as Number).toFloat())
            // Upstream measured negative power during charging and regen on a retail EX30.
            // Convert to the wire convention of positive mW into the battery.
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
                EvChargeState.STATE_CHARGING -> Wire("charge_state", "charging")
                EvChargeState.STATE_NOT_CHARGING -> Wire("charge_state", "idle")
                EvChargeState.STATE_FULLY_CHARGED -> Wire("charge_state", "full")
                EvChargeState.STATE_ERROR -> Wire("charge_state", "fault")
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

    private fun gearName(gear: Int): String = when (gear) {
        VehicleGear.GEAR_NEUTRAL -> "N"
        VehicleGear.GEAR_REVERSE -> "R"
        VehicleGear.GEAR_PARK -> "P"
        VehicleGear.GEAR_DRIVE, in VehicleGear.GEAR_FIRST..VehicleGear.GEAR_NINTH -> "D"
        else -> "UNKNOWN"
    }
}
