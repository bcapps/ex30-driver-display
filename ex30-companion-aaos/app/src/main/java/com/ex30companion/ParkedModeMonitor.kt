package com.ex30companion

import android.car.VehicleGear
import android.car.VehiclePropertyIds
import android.car.hardware.property.EvChargeState
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.PowerManager
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlin.math.abs

private const val WALKING_PACE_MPS = 5f / 3.6f

class DisplaySample(
    val values: Map<Int, Any> = emptyMap(),
    val startCue: String? = null,
    private val beforeDrive: Boolean = true
) {
    fun next(values: Map<Int, Any>, resting: Boolean): DisplaySample {
        val gear = values[VehiclePropertyIds.GEAR_SELECTION] as? Int
        val speed = (values[VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY] as? Number)?.toFloat()
        val moving = speed != null && speed.isFinite() && speed != 0f
        val outOfPark = gear != null && gear != VehicleGear.GEAR_UNKNOWN && gear != VehicleGear.GEAR_PARK
        val before = !outOfPark && !moving && (resting || beforeDrive)
        val drivingGear = gear == VehicleGear.GEAR_DRIVE || gear == VehicleGear.GEAR_REVERSE
        val cue = when {
            before && gear == VehicleGear.GEAR_PARK && speed == 0f -> "welcome"
            // An unbroken sequence from welcome through the first low-speed departure.
            startCue != null && drivingGear && speed != null && abs(speed) <= WALKING_PACE_MPS -> "ready"
            else -> null
        }
        return DisplaySample(values, cue, before)
    }
}

/** Retail EX30 changes to ACC after locking. Plugged-in cars can keep showing charge. */
class ParkedModeMonitor(private val context: Context, scope: CoroutineScope) {
    private val parked = MutableStateFlow(false)
    val state = parked.asStateFlow()
    @Volatile var sample = DisplaySample()
        private set
    private var screenOn = context.getSystemService(PowerManager::class.java).isInteractive

    private val screen = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            screenOn = intent.action == Intent.ACTION_SCREEN_ON
            update(VehicleStateRepository.state.value)
        }
    }

    init {
        ContextCompat.registerReceiver(context, screen, IntentFilter().apply {
            addAction(Intent.ACTION_SCREEN_ON)
            addAction(Intent.ACTION_SCREEN_OFF)
        }, ContextCompat.RECEIVER_NOT_EXPORTED)
        scope.launch { VehicleStateRepository.state.collect(::update) }
    }

    private fun update(values: Map<Int, Any>) {
        val ignition = values[VehiclePropertyIds.IGNITION_STATE] as? Int
        val connected = values[VehiclePropertyIds.EV_CHARGE_PORT_CONNECTED] as? Boolean
            ?: when (values[VehiclePropertyIds.EV_CHARGE_STATE]) {
                EvChargeState.STATE_CHARGING, EvChargeState.STATE_FULLY_CHARGED, EvChargeState.STATE_ERROR -> true
                else -> false
            }
        val resting = !screenOn || ignition in 1..3
        sample = sample.next(values, resting)
        parked.value = !connected && resting
    }

    fun release() = context.unregisterReceiver(screen)
}
