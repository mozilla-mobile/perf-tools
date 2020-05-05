/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

package org.mozilla.perf.investigations

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import android.view.LayoutInflater
import android.view.View
import android.view.ViewTreeObserver
import android.widget.PopupWindow
import androidx.appcompat.app.AppCompatActivity
import kotlinx.android.synthetic.main.activity_main.*
import org.mozilla.perf.investigations.DurationTimes.duration

private val uiHandler = Handler(Looper.getMainLooper())

/**
 * See <proj-root>/README.md for details on this experiment.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var preinflatedPopupWindowLayout: View

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        preinflatedPopupWindowLayout = LayoutInflater.from(this).inflate(R.layout.popup_window_preinflated, null, false)

        popupWindowButton.setOnClickListener {
            Log.e("lol", "popupWindowButton.onClick")
            DurationTimes.start = SystemClock.elapsedRealtime()
            showPopupWindow()
        }

        popupWindowPreinflatedButton.setOnClickListener {
            Log.e("lol", "popupWindowPreinflatedButton.onClick")
            DurationTimes.start = SystemClock.elapsedRealtime()
            showPopupWindowPreinflated()
        }
    }

    private fun showPopupWindow() {
        val layout = LayoutInflater.from(this).inflate(R.layout.popup_window, null, false)

        val window = PopupWindow(layout, 500, 500, true)
        window.showAsDropDown(popupWindowButton)
        window.showAtLocation(contentContainer, 0, 200, 200)

        // For an unknown reason, the onDraw method never gets called if this is attached to the layout
        // in the PopupWindow so we set it on the contentContainer instead.
        contentContainer.viewTreeObserver.addOnDrawListener(DrawOnce(contentContainer, "PopupWindow duration"))

        // Apparently tapping outside a popup window to dismiss is custom behavior so we do the
        // simple thing and hide them after a few seconds
        uiHandler.postDelayed({
            window.dismiss()
        }, 2000)
    }

    private fun showPopupWindowPreinflated() {
        val window = PopupWindow(preinflatedPopupWindowLayout, 500, 500, true)
        window.showAsDropDown(popupWindowPreinflatedButton)
        window.showAtLocation(contentContainer, 0, 200, 200)

        // For an unknown reason, the onDraw method never gets called if this is attached to the layout
        // in the PopupWindow so we set it on the contentContainer instead.
        contentContainer.viewTreeObserver.addOnDrawListener(DrawOnce(contentContainer, "PopupWindow Preinflated duration"))

        // Apparently tapping outside a popup window to dismiss is custom behavior so we do the
        // simple thing and hide them after a few seconds
        uiHandler.postDelayed({
            window.dismiss()
        }, 2000)
    }
}

private class DrawOnce(
    private val view: View,
    private val logMsg: String
) : ViewTreeObserver.OnDrawListener {

    override fun onDraw() {
        DurationTimes.end = SystemClock.elapsedRealtime()

        // For an unknown reason, this is called twice on the GS5 so we need to trim the redundant
        // measurement from the log before taking the measurement.
        Log.e("lol", "$logMsg: $duration ms")

        uiHandler.post {
            view.viewTreeObserver.removeOnDrawListener(this)
        }
    }
}

object DurationTimes {
    var start = -1L
    var end = -1L

    val duration: Long get() = end - start
}
