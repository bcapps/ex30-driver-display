package com.ex30companion

import android.car.Car
import android.car.VehiclePropertyIds.PERF_ODOMETER
import android.car.VehiclePropertyIds.TURN_SIGNAL_LIGHT_STATE
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OptionalInstrumentsTest {
    @Test fun lampReportsPreserveBothBitsAndTheOffPulse() {
        assertEquals(Car.PERMISSION_READ_EXTERIOR_LIGHTS, PropertyCatalog.permissions[TURN_SIGNAL_LIGHT_STATE])
        for (mask in listOf(1, 0, 2, 0, 3, 0)) {
            assertEquals(WireFieldMapper.Wire("turn_signal_lights", mask), WireFieldMapper.map(TURN_SIGNAL_LIGHT_STATE, mask))
        }
        for (invalid in listOf(null, -1, 4, 5, 1f, true)) {
            assertNull(WireFieldMapper.map(TURN_SIGNAL_LIGHT_STATE, invalid))
        }
    }

    @Test fun odometerReportsVehicleKilometresInWireMetresIncludingZero() {
        assertEquals(Car.PERMISSION_MILEAGE_3P, PropertyCatalog.permissions[PERF_ODOMETER])
        assertEquals(WireFieldMapper.Wire("odometer_m", 0.0), WireFieldMapper.map(PERF_ODOMETER, 0f))
        assertEquals(WireFieldMapper.Wire("odometer_m", 1_897_750.0), WireFieldMapper.map(PERF_ODOMETER, 1897.75f))
        for (invalid in listOf(null, -1f, Float.NaN, Float.POSITIVE_INFINITY, "1897", true)) {
            assertNull(WireFieldMapper.map(PERF_ODOMETER, invalid))
        }
    }
}
