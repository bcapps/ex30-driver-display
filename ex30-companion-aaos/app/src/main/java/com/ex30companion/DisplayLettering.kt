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
    private val digitsAndGears = "0123456789PRND".map(Char::toString)
    private val readings = digitsAndGears + listOf("km/h", "mph", "m/s", "mi", "km", "m", "%", "–")
    private fun novum(weight: String) =
        Typeface.create("VolvoNovum-$weight", Typeface.NORMAL).takeUnless { it == Typeface.DEFAULT }

    private fun inter(assets: AssetManager, weight: Int) = Typeface.Builder(assets, "InterVariable.ttf")
        .setFontVariationSettings("'wght' $weight").build()

    fun frame(assets: AssetManager): String {
        val regular = novum("Regular")
        val semiLight = novum("SemiLight")
        val gearFace = semiLight ?: Typeface.create("sans-serif-light", Typeface.NORMAL)
        val selectedGearFace = novum("Medium") ?: Typeface.create("sans-serif-medium", Typeface.NORMAL)
        val speedFace = regular ?: inter(assets, 360)
        val readingFace = semiLight ?: inter(assets, 330)
        val instruments = readings + digitsAndGears
        val captions = listOf(
            Triple("Charging", 72, speedFace), Triple("Done in", 72, readingFace),
            Triple("h", 72, readingFace), Triple("min", 72, readingFace),
            Triple("kW", 72, readingFace), Triple(".", 72, readingFace),
            Triple("Hello", 88, selectedGearFace), Triple("Press the brake and select D or R to start", 32, readingFace),
            Triple("Plugged in", 64, speedFace), Triple("Target reached", 64, speedFace),
            Triple("Charging fault", 64, speedFace), Triple("°C", 64, readingFace),
            Triple("°F", 64, readingFace), Triple("−", 64, readingFace)
        )
        val captionTop = (instruments.size + 5) / 6 * 192
        val bitmap = Bitmap.createBitmap(1920, captionTop + (captions.size + 2) / 3 * 96, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.SUBPIXEL_TEXT_FLAG).apply { color = Color.WHITE }
        val advances = JSONArray()
        fun draw(label: String, face: Typeface, size: Int, x: Int, baseline: Int, features: String? = null) {
            paint.typeface = face
            paint.textSize = size.toFloat()
            paint.fontFeatureSettings = features
            canvas.drawText(label, (x + 4).toFloat(), baseline.toFloat(), paint)
            advances.put(paint.measureText(label).toDouble())
        }
        for ((i, label) in instruments.withIndex()) {
            val selected = i >= readings.size
            val digit = label[0].isDigit()
            val face = when {
                digit -> if (selected) speedFace else readingFace
                label in listOf("P", "R", "N", "D") -> if (selected) selectedGearFace else gearFace
                label in listOf("km", "mi", "m", "%") -> readingFace
                else -> regular ?: Typeface.DEFAULT
            }
            val features = when {
                digit -> "'lnum' 1, 'tnum' 1"
                label == "%" -> "'case' 1"
                else -> null
            }
            draw(label, face, if (digit) 216 else 128, i % 6 * 320, i / 6 * 192 + (if (digit) 174 else 150), features)
        }
        for ((i, caption) in captions.withIndex()) {
            val (label, size, face) = caption
            draw(label, face, size, i % 3 * 640, captionTop + i / 3 * 96 + 72)
        }
        val png = ByteArrayOutputStream().use {
            bitmap.compress(Bitmap.CompressFormat.PNG, 100, it)
            bitmap.recycle()
            Base64.encodeToString(it.toByteArray(), Base64.NO_WRAP)
        }
        return JSONObject().put("type", "lettering").put("version", 2)
            .put("advances", advances).put("png", png).toString()
    }
}
