package com.ex30companion

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.bluetooth.BluetoothManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.IBinder
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

class BridgeService : Service() {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private lateinit var car: CarPropertyService
    private lateinit var monitor: ParkedModeMonitor
    private var link: BridgeClient? = null
    private var granted: Set<String>? = null

    override fun onCreate() {
        super.onCreate()
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel("display", "Driver display", NotificationManager.IMPORTANCE_LOW)
        )
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        startForeground(1, NotificationCompat.Builder(this, "display")
            .setSmallIcon(R.drawable.ic_display).setContentTitle(getString(R.string.app_name))
            .setContentText("Bluetooth display service").setContentIntent(open).setOngoing(true).build())

        car = CarPropertyService(this)
        monitor = ParkedModeMonitor(this, scope)
        link = getSystemService(BluetoothManager::class.java).adapter?.let { BridgeClient(this, it) }
        scope.launch {
            monitor.state.collect {
                car.setParked(it)
                updateLink()
            }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!canStart(this)) {
            stopSelf()
            return START_NOT_STICKY
        }
        val permissions = PropertyCatalog.dangerousPermissions.filter {
            checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED
        }.toSet()
        if (permissions != granted) {
            car.stop()
            granted = permissions
            car.start()
        }
        updateLink()
        return START_STICKY
    }

    private fun updateLink() {
        link?.setTarget(if (monitor.state.value) null else BridgeSettings.address(this))
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        link?.setTarget(null)
        monitor.release()
        scope.cancel()
        car.stop()
        super.onDestroy()
    }

    companion object {
        private fun canStart(context: Context) = BridgeSettings.address(context) != null &&
            context.checkSelfPermission(Manifest.permission.BLUETOOTH_CONNECT) == PackageManager.PERMISSION_GRANTED

        fun start(context: Context) {
            if (canStart(context)) context.startForegroundService(Intent(context, BridgeService::class.java))
        }
    }
}
