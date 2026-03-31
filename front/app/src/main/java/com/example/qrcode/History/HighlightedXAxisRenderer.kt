package com.example.qrcode.History

import android.graphics.Canvas
import com.github.mikephil.charting.components.XAxis
import com.github.mikephil.charting.renderer.XAxisRenderer
import com.github.mikephil.charting.utils.MPPointF
import com.github.mikephil.charting.utils.Transformer
import com.github.mikephil.charting.utils.ViewPortHandler

class HighlightedXAxisRenderer(
    viewPortHandler: ViewPortHandler,
    xAxis: XAxis,
    trans: Transformer,
    private val todayIndex: Int,
    private val normalColor: Int,
    private val highlightColor: Int
) : XAxisRenderer(viewPortHandler, xAxis, trans) {

    override fun drawLabel(
        c: Canvas,
        formattedLabel: String,
        x: Float,
        y: Float,
        anchor: MPPointF,
        angleDegrees: Float
    ) {
        // 오늘 요일이면 강조 색상, 아니면 기본 색상
        mAxisLabelPaint.color =
            if (formattedLabel == mXAxis.valueFormatter.getFormattedValue(todayIndex.toFloat())) {
                highlightColor
            } else {
                normalColor
            }


        super.drawLabel(c, formattedLabel, x, y, anchor, angleDegrees)
    }
}
