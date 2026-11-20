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
    private val chargingLabels = listOf("Charging", "Done in", "h", "min", "kW", ".")
    private val welcomeLabels = listOf("Hello", "Press the brake and select D or R to start")
    private fun novum(weight: String) =
        Typeface.create("VolvoNovum-$weight", Typeface.NORMAL).takeUnless { it == Typeface.DEFAULT }

    private fun inter(assets: AssetManager, weight: Int) = Typeface.Builder(assets, "InterVariable.ttf")
        .setFontVariationSettings("'wght' $weight").build()

    fun frame(assets: AssetManager): String {
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.SUBPIXEL_TEXT_FLAG).apply {
            color = Color.WHITE
        }
        // Six cells per row leave room for complete unit labels like km/h.
        val regular = novum("Regular")
        val semiLight = novum("SemiLight")
        val gearFaces = listOf(semiLight ?: Typeface.create("sans-serif-light", Typeface.NORMAL),
            novum("Medium") ?: Typeface.create("sans-serif-medium", Typeface.NORMAL))
        val speedFace = regular ?: inter(assets, 360)
        val readingFace = semiLight ?: inter(assets, 330)
        val widths = JSONArray()
        val bitmap = Bitmap.createBitmap(CELL * 6, 192 * 4 * gearFaces.size, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        for ((row, gearFace) in gearFaces.withIndex()) {
            val advances = JSONArray()
            for ((i, label) in labels.withIndex()) {
                val digit = i < 10
                paint.typeface = when {
                    digit -> if (row == 1) speedFace else readingFace
                    label == "km" || label == "mi" || label == "m" || label == "%" -> readingFace
                    label.length == 1 && label[0] in "PRND" -> gearFace
                    else -> regular ?: Typeface.DEFAULT
                }
                paint.fontFeatureSettings = when {
                    digit -> "'lnum' 1, 'tnum' 1"
                    label == "%" -> "'case' 1"
                    else -> null
                }
                paint.textSize = if (digit) 216f else 128f
                val baseline = if (digit) 174 else 150
                canvas.drawText(label, (i % 6 * CELL + 4).toFloat(),
                    (row * 768 + i / 6 * 192 + baseline).toFloat(), paint)
                advances.put(paint.measureText(label).toDouble())
            }
            widths.put(advances)
        }
        // The last two cells of each block are unused by the driving display.
        val chargingWidths = JSONArray()
        paint.textSize = 72f
        paint.fontFeatureSettings = null
        for ((i, label) in chargingLabels.withIndex()) {
            paint.typeface = if (i == 0) speedFace else readingFace
            val x = (4 + i % 2) * CELL + 4
            val y = i / 4 * 768 + 576 + i / 2 % 2 * 96 + 74
            canvas.drawText(label, x.toFloat(), y.toFloat(), paint)
            chargingWidths.put(paint.measureText(label).toDouble())
        }
        // Two lines share the final 640 × 96 strip of the existing atlas.
        val welcomeWidths = JSONArray()
        for ((i, label) in welcomeLabels.withIndex()) {
            paint.typeface = if (i == 0) gearFaces[1] else readingFace
            paint.textSize = if (i == 0) 88f else 32f
            canvas.drawText(label, (4 * CELL + 4).toFloat(), if (i == 0) 1507f else 1534f, paint)
            welcomeWidths.put(paint.measureText(label).toDouble())
        }
        val png = ByteArrayOutputStream().use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
            it.toByteArray()
        }
        bitmap.recycle()
        return JSONObject().put("type", "lettering").put("version", 1).put("speedRow", 1)
            .put("labels", JSONArray(labels)).put("advances", widths).put("chargingAdvances", chargingWidths)
            .put("welcomeAdvances", welcomeWidths).put("png", Base64.encodeToString(png, Base64.NO_WRAP)).toString()
    }
}
