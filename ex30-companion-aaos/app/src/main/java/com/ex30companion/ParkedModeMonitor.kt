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

/** Retail EX30 changes to ACC after locking. Plugged-in cars can keep showing charge. */
class ParkedModeMonitor(private val context: Context, scope: CoroutineScope) {
    private val parked = MutableStateFlow(false)
    val state = parked.asStateFlow()
    @Volatile var beforeDrive = true
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
            ?: (values[VehiclePropertyIds.EV_CHARGE_STATE] == EvChargeState.STATE_CHARGING)
        val resting = !screenOn || ignition in 1..3
        val gear = values[VehiclePropertyIds.GEAR_SELECTION] as? Int
        val speed = (values[VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY] as? Number)?.toFloat()
        if ((gear != null && gear != VehicleGear.GEAR_UNKNOWN && gear != VehicleGear.GEAR_PARK) ||
            (speed != null && speed.isFinite() && speed != 0f)) {
            beforeDrive = false
        } else if (resting) {
            beforeDrive = true
        }
        parked.value = !connected && resting
    }

    fun release() = context.unregisterReceiver(screen)
}
