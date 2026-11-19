package com.ex30companion

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

/** Only available vehicle values belong in a full display snapshot. */
object VehicleStateRepository {
    private val values = MutableStateFlow(emptyMap<Int, Any>())
    val state = values.asStateFlow()

    fun clear() {
        values.value = emptyMap()
    }

    fun update(id: Int, value: Any?) {
        values.update { old ->
            when {
                old[id] == value -> old
                value == null -> old - id
                else -> old + (id to value)
            }
        }
    }
}
