package com.ex30companion

import android.Manifest
import android.annotation.SuppressLint
import android.bluetooth.BluetoothAdapter
import android.bluetooth.BluetoothDevice
import android.bluetooth.BluetoothManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Bundle
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import com.ex30companion.databinding.ActivityMainBinding
import com.ex30companion.databinding.DisplayChoiceBinding

/** A parked setup screen. Only an explicit selection can create a new bond. */
@SuppressLint("MissingPermission")
class MainActivity : AppCompatActivity() {
    private lateinit var ui: ActivityMainBinding
    private val adapter get() = getSystemService(BluetoothManager::class.java).adapter
    private val listed = mutableSetOf<String>()
    private var pending: String? = null
    private var searching = false
    private val permissions = listOf(Manifest.permission.BLUETOOTH_CONNECT, Manifest.permission.BLUETOOTH_SCAN)

    private val requestAccess = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        if (hasBluetoothAccess()) findDisplays() else ui.status.setText(R.string.nearby_required)
    }
    private val enableRadio = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) {
        if (adapter?.isEnabled == true) findDisplays() else ui.status.setText(R.string.bluetooth_off)
    }

    private val events = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (!hasBluetoothAccess()) return
            @Suppress("DEPRECATION")
            val device = intent.getParcelableExtra<BluetoothDevice>(BluetoothDevice.EXTRA_DEVICE)
            when (intent.action) {
                BluetoothDevice.ACTION_FOUND -> if (searching && device != null) listDevice(device)
                BluetoothAdapter.ACTION_DISCOVERY_FINISHED -> if (searching) {
                    searching = false
                    ui.find.isEnabled = true
                    ui.status.setText(if (listed.isEmpty()) R.string.none_found else R.string.select_display)
                }
                BluetoothDevice.ACTION_BOND_STATE_CHANGED -> if (device != null && device.address == pending) {
                    when (device.bondState) {
                        BluetoothDevice.BOND_BONDED -> select(device)
                        BluetoothDevice.BOND_NONE -> {
                            pending = null
                            ui.find.isEnabled = true
                            ui.status.setText(R.string.pairing_cancelled)
                        }
                    }
                }
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        ui = ActivityMainBinding.inflate(layoutInflater)
        setContentView(ui.root)
        pending = savedInstanceState?.getString("pairing")
        ContextCompat.registerReceiver(this, events, IntentFilter().apply {
            addAction(BluetoothDevice.ACTION_FOUND)
            addAction(BluetoothDevice.ACTION_BOND_STATE_CHANGED)
            addAction(BluetoothAdapter.ACTION_DISCOVERY_FINISHED)
        }, ContextCompat.RECEIVER_EXPORTED)
        showSelected()
        ui.find.setOnClickListener {
            val needed = (permissions + PropertyCatalog.dangerousPermissions).filter {
                checkSelfPermission(it) != PackageManager.PERMISSION_GRANTED
            }
            if (needed.isEmpty()) findDisplays() else requestAccess.launch(needed.toTypedArray())
        }
    }

    override fun onResume() {
        super.onResume()
        if (hasBluetoothAccess()) pending?.let { address ->
            adapter?.bondedDevices?.firstOrNull { it.address == address }?.let(::select)
        }
        BridgeService.start(this)
    }

    override fun onSaveInstanceState(state: Bundle) {
        state.putString("pairing", pending)
        super.onSaveInstanceState(state)
    }

    private fun hasBluetoothAccess() = permissions.all { checkSelfPermission(it) == PackageManager.PERMISSION_GRANTED }

    private fun findDisplays() {
        val radio = adapter ?: return ui.status.setText(R.string.bluetooth_off)
        if (!radio.isEnabled) {
            enableRadio.launch(Intent(BluetoothAdapter.ACTION_REQUEST_ENABLE))
            return
        }
        ui.devices.removeAllViews()
        listed.clear()
        pending = null
        radio.bondedDevices.forEach(::listDevice)
        searching = radio.isDiscovering || radio.startDiscovery()
        ui.find.isEnabled = !searching
        ui.status.setText(when {
            searching -> R.string.searching
            listed.isNotEmpty() -> R.string.select_display
            else -> R.string.search_failed
        })
    }

    private fun listDevice(device: BluetoothDevice) {
        val name = device.name ?: return
        if (name != BridgeSettings.DISPLAY_NAME && !name.startsWith(BridgeSettings.DISPLAY_NAME + " ")) return
        if (!listed.add(device.address)) return
        val choice = DisplayChoiceBinding.inflate(layoutInflater, ui.devices, false).root
        choice.text = name
        choice.setOnClickListener { pair(device) }
        ui.devices.addView(choice)
    }

    private fun pair(device: BluetoothDevice) {
        searching = false
        adapter?.cancelDiscovery()
        ui.devices.removeAllViews()
        if (device.bondState == BluetoothDevice.BOND_BONDED) {
            select(device)
            return
        }
        pending = device.address
        ui.find.isEnabled = false
        ui.status.setText(R.string.confirm_pair)
        if (device.bondState != BluetoothDevice.BOND_BONDING && !device.createBond()) {
            pending = null
            ui.find.isEnabled = true
            ui.status.setText(R.string.pairing_cancelled)
        }
    }

    private fun select(device: BluetoothDevice) {
        pending = null
        BridgeSettings.select(this, device.address)
        BridgeService.start(this)
        ui.devices.removeAllViews()
        showSelected()
    }

    private fun showSelected() {
        ui.find.isEnabled = true
        val address = BridgeSettings.address(this)
        if (address != null && hasBluetoothAccess()) {
            val device = adapter?.bondedDevices?.firstOrNull { it.address == address }
            if (device != null) {
                ui.status.text = getString(R.string.saved_display, device.name ?: BridgeSettings.DISPLAY_NAME)
                return
            }
        }
        ui.status.setText(R.string.setup_hint)
    }

    override fun onDestroy() {
        unregisterReceiver(events)
        if (searching && hasBluetoothAccess()) adapter?.cancelDiscovery()
        super.onDestroy()
    }
}
