package com.ex30companion

import android.content.res.AssetManager
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
    private fun novum(weight: String) =
        Typeface.create("VolvoNovum-$weight", Typeface.NORMAL).takeUnless { it == Typeface.DEFAULT }

    fun frame(assets: AssetManager): String {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.SUBPIXEL_TEXT_FLAG).apply {
            color = Color.WHITE
        }
        // Six cells per row leave room for complete unit labels like km/h.
        val faces = listOf(novum("Regular") ?: Typeface.DEFAULT,
            novum("Medium") ?: Typeface.create("sans-serif-medium", Typeface.NORMAL))
        val semiLight = novum("SemiLight")
        val inactiveGear = semiLight ?: Typeface.create("sans-serif-light", Typeface.NORMAL)
        val speedFace = semiLight ?: Typeface.Builder(assets, "InterVariable.ttf")
            .setFontVariationSettings("'wght' 330").build()
        val widths = JSONArray()
        val bitmap = Bitmap.createBitmap(CELL * 6, 192 * 4 * faces.size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        for ((row, face) in faces.withIndex()) {
            val advances = JSONArray()
            for ((i, label) in labels.withIndex()) {
                val digit = i < 10
                paint.typeface = when {
                    row == 1 && digit -> speedFace
                    row == 0 && label.length == 1 && label[0] in "PRND" -> inactiveGear
                    else -> face
                }
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
        return JSONObject().put("type", "lettering").put("version", 1).put("speedRow", 1)
            .put("labels", JSONArray(labels)).put("advances", widths)
            .put("png", Base64.encodeToString(png, Base64.NO_WRAP)).toString()
    }
}
