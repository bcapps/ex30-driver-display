package com.ex30companion

import android.content.Context

object BridgeSettings {
    const val DISPLAY_NAME = "EX30 Display"
    private fun prefs(context: Context) = context.getSharedPreferences("display", Context.MODE_PRIVATE)
    fun address(context: Context): String? = prefs(context).getString("address", null)
    fun select(context: Context, address: String) = prefs(context).edit().putString("address", address).apply()
}
