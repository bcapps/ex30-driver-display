package com.ex30companion

import android.car.VehicleGear.GEAR_DRIVE
import android.car.VehicleGear.GEAR_NEUTRAL
import android.car.VehicleGear.GEAR_PARK
import android.car.VehicleGear.GEAR_REVERSE
import android.car.VehiclePropertyIds.GEAR_SELECTION
import android.car.VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class DisplaySampleTest {
    private fun DisplaySample.at(gear: Int, speed: Float, resting: Boolean = false) =
        next(mapOf(GEAR_SELECTION to gear, PERF_VEHICLE_SPEED_DISPLAY to speed), resting)

    @Test fun readyShowsOnceInEitherDirectionUntilWalkingPace() {
        for ((gear, direction) in listOf(GEAR_DRIVE to 1f, GEAR_REVERSE to -1f)) {
            val parked = DisplaySample().at(GEAR_PARK, 0f)
            assertEquals("welcome", parked.startCue)
            val ready = parked.at(gear, 0f)
            assertEquals("ready", ready.startCue)
            val creeping = ready.at(gear, direction * 5f / 3.6f)
            assertEquals("ready", creeping.startCue)
            val moving = creeping.at(gear, direction * 1.5f)
            assertNull(moving.startCue)
            val trafficLight = moving.at(gear, 0f)
            assertNull(trafficLight.startCue)
            val parkedAgain = trafficLight.at(GEAR_PARK, 0f)
            assertNull(parkedAgain.at(gear, 0f).startCue)
            val nextTrip = parkedAgain.at(GEAR_PARK, 0f, resting = true).at(GEAR_PARK, 0f)
            assertEquals("ready", nextTrip.at(gear, 0f).startCue)
        }
    }

    @Test fun firstReadingInDriveOrAnInterruptedDepartureDoesNotShowReady() {
        assertNull(DisplaySample().at(GEAR_DRIVE, 0f).startCue)
        val parked = DisplaySample().at(GEAR_PARK, 0f)
        assertNull(parked.at(GEAR_NEUTRAL, 0f).startCue)
        val ready = parked.at(GEAR_REVERSE, 0f)
        assertNull(ready.at(GEAR_PARK, 0f).at(GEAR_DRIVE, 0f).startCue)
        val missingSpeed = ready.next(mapOf(GEAR_SELECTION to GEAR_REVERSE), resting = false)
        assertNull(missingSpeed.startCue)
        assertNull(missingSpeed.at(GEAR_REVERSE, 0f).startCue)
    }
}
