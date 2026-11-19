package com.ex30companion

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Typeface
import android.util.Base64
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream

/**
 * Render the few labels the Pi needs with the head unit's installed typefaces.
 * Each row is white on transparent and has one common baseline. The Pi tints
 * the pixels for day/night and reuses them for the whole connection.
 */
object DisplayLettering {
    private const val CELL = 320
    private val labels = listOf("0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "P", "R", "N", "D", "km/h", "mph", "m/s", "mi", "km", "m", "%", "–")
    private fun installed(name: String, fallback: String): Typeface {
        val face = Typeface.create("VolvoNovum-$name", Typeface.NORMAL)
        return if (face == Typeface.DEFAULT) Typeface.create(fallback, Typeface.NORMAL) else face
    }

    fun frame(): String {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.SUBPIXEL_TEXT_FLAG).apply {
            color = Color.WHITE
        }
        // Six cells per row leave room for complete unit labels like km/h.
        val faces = listOf(installed("Regular", "sans-serif"), installed("Medium", "sans-serif-medium"))
        val inactiveGear = installed("SemiLight", "sans-serif-light")
        val widths = JSONArray()
        val bitmap = Bitmap.createBitmap(CELL * 6, 192 * 4 * faces.size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        for ((row, face) in faces.withIndex()) {
            val advances = JSONArray()
            for ((i, label) in labels.withIndex()) {
                // Large speed numerals reach the panel at native resolution.
                paint.typeface = if (row == 0 && label.length == 1 && label[0] in "PRND") inactiveGear else face
                val digit = i < 10
                paint.textSize = if (digit) 216f else 128f
                val baseline = if (digit) 174 else 150
                canvas.drawText(label, (i % 6 * CELL + 4).toFloat(),
                    (row * 768 + i / 6 * 192 + baseline).toFloat(), paint)
                advances.put(paint.measureText(label).toDouble())
            }
            widths.put(advances)
        }
        val png = ByteArrayOutputStream().use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
            it.toByteArray()
        }
        bitmap.recycle()
        return JSONObject().put("type", "lettering").put("version", 1)
            .put("labels", JSONArray(labels)).put("advances", widths)
            .put("png", Base64.encodeToString(png, Base64.NO_WRAP)).toString()
    }
}
