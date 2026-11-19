package com.ex30companion

import android.car.Car
import android.car.VehiclePropertyIds
import android.car.hardware.CarPropertyConfig
import android.car.hardware.CarPropertyValue
import android.car.hardware.property.CarPropertyManager
import android.content.Context
import android.content.pm.PackageManager
import android.util.Log

/** Subscriptions and lifecycle callbacks run on the main looper. */
class CarPropertyService(private val context: Context) {
    private var car: Car? = null
    private var manager: CarPropertyManager? = null
    private var callback: CarPropertyManager.CarPropertyEventCallback? = null
    private var generation = 0
    private var parked = false

    fun start() {
        if (car != null) return
        val session = ++generation
        car = Car.createCar(context, null, Car.CAR_WAIT_TIMEOUT_DO_NOT_WAIT) { connection, ready ->
            if (session != generation) return@createCar
            VehicleStateRepository.clear()
            callback = null
            manager = if (ready) connection.getCarManager(Car.PROPERTY_SERVICE) as? CarPropertyManager else null
            val mgr = manager ?: return@createCar
            val observer = object : CarPropertyManager.CarPropertyEventCallback {
                override fun onChangeEvent(value: CarPropertyValue<*>) {
                    if (callback === this && (!parked || value.propertyId in wakeProperties)) publish(value)
                }

                override fun onErrorEvent(propId: Int, area: Int) {
                    if (callback === this) VehicleStateRepository.update(propId, null)
                }
            }
            callback = observer
            for (id in PropertyCatalog.permissions.keys) {
                if (!parked || id in wakeProperties) subscribe(mgr, observer, id)
            }
        }
    }

    fun setParked(value: Boolean) {
        if (parked == value) return
        parked = value
        val mgr = manager ?: return
        val observer = callback ?: return
        for (id in PropertyCatalog.permissions.keys - wakeProperties) {
            if (parked) {
                runCatching { mgr.unregisterCallback(observer, id) }
                VehicleStateRepository.update(id, null)
            } else subscribe(mgr, observer, id)
        }
    }

    fun stop() {
        generation++
        callback?.let { runCatching { manager?.unregisterCallback(it) } }
        callback = null
        manager = null
        car?.disconnect()
        car = null
        VehicleStateRepository.clear()
    }

    private fun subscribe(mgr: CarPropertyManager, observer: CarPropertyManager.CarPropertyEventCallback, id: Int) {
        if (context.checkSelfPermission(PropertyCatalog.permissions.getValue(id)) != PackageManager.PERMISSION_GRANTED) return
        try {
            val config = mgr.getCarPropertyConfig(id) ?: return
            when (config.changeMode) {
                CarPropertyConfig.VEHICLE_PROPERTY_CHANGE_MODE_STATIC -> publish(mgr.getProperty<Any>(id, 0))
                CarPropertyConfig.VEHICLE_PROPERTY_CHANGE_MODE_CONTINUOUS -> {
                    val hz = when (id) {
                        VehiclePropertyIds.PERF_VEHICLE_SPEED_DISPLAY -> 10f
                        VehiclePropertyIds.EV_BATTERY_INSTANTANEOUS_CHARGE_RATE -> 20f
                        else -> 1f
                    }.coerceIn(config.minSampleRate, config.maxSampleRate)
                    mgr.registerCallback(observer, id, hz)
                }
                else -> mgr.registerCallback(observer, id, CarPropertyManager.SENSOR_RATE_ONCHANGE)
            }
        } catch (failure: RuntimeException) {
            Log.d("CalmDisplay", "Property 0x${id.toString(16)} unavailable", failure)
            VehicleStateRepository.update(id, null)
        }
    }

    private fun publish(value: CarPropertyValue<*>) {
        VehicleStateRepository.update(value.propertyId,
            if (value.status == CarPropertyValue.STATUS_AVAILABLE) value.value else null)
    }

    private val wakeProperties = setOf(VehiclePropertyIds.IGNITION_STATE, VehiclePropertyIds.EV_CHARGE_PORT_CONNECTED,
        VehiclePropertyIds.EV_CHARGE_STATE)
}
