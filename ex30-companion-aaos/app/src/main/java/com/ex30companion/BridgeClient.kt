package com.ex30companion

import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothSocket
import android.content.Context
import android.content.res.Configuration
import android.os.SystemClock
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import org.json.JSONObject
import java.io.IOException
import java.util.UUID

/** One bonded display, one writer, and no queue of old speed readings. */
@SuppressLint("MissingPermission") // BridgeService checks BLUETOOTH_CONNECT before starting.
class BridgeClient(private val context: Context, private val adapter: BluetoothAdapter,
                   private val monitor: ParkedModeMonitor) {
    private val scope = CoroutineScope(Dispatchers.IO)
    private val lettering by lazy { DisplayLettering.frame(context.assets) }
    private var target: String? = null
    private var job: Job? = null
    private var socket: BluetoothSocket? = null

    @Synchronized
    fun setTarget(address: String?) {
        if (address == target) return
        target = address
        job?.cancel()
        // close() also interrupts a blocking connect or write on the IO thread.
        runCatching { socket?.close() }
        socket = null
        job = address?.let { scope.launch { reconnect(it) } }
    }

    @Synchronized
    private fun open(address: String, worker: Job): BluetoothSocket? {
        if (!worker.isActive || target != address || !adapter.isEnabled) return null
        val device = adapter.bondedDevices.firstOrNull { it.address == address } ?: return null
        return device.createRfcommSocketToServiceRecord(SERVICE_UUID).also { socket = it }
    }

    private suspend fun CoroutineScope.reconnect(address: String) {
        var retryMs = 1000L
        val worker = coroutineContext[Job]!!
        while (isActive) {
            try {
                open(address, worker)?.use { link ->
                    link.connect()
                    val writer = link.outputStream.bufferedWriter(Charsets.UTF_8)
                    writer.write(lettering)
                    writer.newLine()
                    writer.flush()
                    retryMs = 1000L
                    var previous: Map<Int, Any>? = null
                    var previousMode = -1
                    var lastSent = 0L
                    while (isActive) {
                        val samples = VehicleStateRepository.state.value
                        val mode = context.resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK
                        val now = SystemClock.elapsedRealtime()
                        if (samples !== previous || mode != previousMode || now - lastSent >= 1000L) {
                            writer.write(snapshot(samples, mode).toString())
                            writer.newLine()
                            writer.flush()
                            previous = samples
                            previousMode = mode
                            lastSent = now
                        }
                        delay(50)
                    }
                }
            } catch (failure: IOException) {
                if (isActive) Log.d("CalmDisplay", "Display disconnected", failure)
            } catch (failure: SecurityException) {
                Log.i("CalmDisplay", "Bluetooth permission unavailable", failure)
            }
            delay(retryMs)
            retryMs = (retryMs * 2).coerceAtMost(8000)
        }
    }

    private fun snapshot(samples: Map<Int, Any>, mode: Int): JSONObject {
        val fields = JSONObject()
        if (monitor.beforeDrive) fields.put("before_drive", true)
        for ((id, value) in samples) {
            val wire = WireFieldMapper.map(id, value) ?: continue
            val v = wire.value
            if (v is Number && !v.toDouble().isFinite()) continue
            fields.put(wire.field, v)
            // Previously paired Pi software still uses this flag.
            if (wire.field == "charge_state") fields.put("charging_active", v == "charging")
        }
        when (mode) {
            Configuration.UI_MODE_NIGHT_YES -> fields.put("night_mode", true)
            Configuration.UI_MODE_NIGHT_NO -> fields.put("night_mode", false)
        }
        val miles = context.resources.configuration.locales[0].country in setOf("US", "GB")
        if (!fields.has("distance_unit")) fields.put("distance_unit", if (miles) "mi" else "km")
        if (!fields.has("speed_unit")) fields.put("speed_unit", if (miles) "mph" else "km/h")
        return JSONObject().put("type", "state").put("fields", fields)
    }

    companion object {
        val SERVICE_UUID: UUID = UUID.fromString("9e457bc1-0291-4dcb-8427-919da22db81f")
    }
}
